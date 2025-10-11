"""
Federation Connection Layer for Brain Swarm

This module handles WebSocket connections to discovered swarms,
including authentication and message exchange for cross-swarm communication.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

from discovery import SwarmMetadata

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states for federation links."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class FederationMessage:
    """Message structure for federation communication."""
    message_id: str
    message_type: str
    sender_swarm_id: str
    target_swarm_id: str
    payload: Dict[str, Any]
    timestamp: float
    requires_response: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FederationMessage':
        return cls(**data)


class FederationConnection:
    """
    WebSocket-based connection to a remote swarm for federation.

    Handles connection lifecycle, authentication, and message exchange.
    """

    def __init__(self,
                 local_swarm_id: str,
                 remote_metadata: SwarmMetadata,
                 auth_token: str,
                 reconnect_interval: float = 30.0,
                 heartbeat_interval: float = 60.0):
        """
        Initialize federation connection.

        Args:
            local_swarm_id: ID of the local swarm
            remote_metadata: Metadata of the remote swarm to connect to
            auth_token: Authentication token for federation
            reconnect_interval: Seconds between reconnection attempts
            heartbeat_interval: Seconds between heartbeat messages
        """
        self.local_swarm_id = local_swarm_id
        self.remote_metadata = remote_metadata
        self.auth_token = auth_token
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval

        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Message handling
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.message_handlers: Dict[str, Callable[[FederationMessage], None]] = {}

        # Callbacks
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_message: Optional[Callable[[FederationMessage], None]] = None

        # WebSocket URI
        self.ws_uri = f"ws://{remote_metadata.host}:{remote_metadata.api_port}/federation"

        logger.info(f"Federation connection initialized to {remote_metadata.swarm_id} at {self.ws_uri}")

    async def connect(self) -> bool:
        """
        Establish connection to the remote swarm.

        Returns:
            True if connection successful, False otherwise
        """
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            logger.warning("Connection already in progress or established")
            return self.state == ConnectionState.CONNECTED

        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to {self.remote_metadata.swarm_id}...")

        try:
            # Establish WebSocket connection
            self.websocket = await websockets.connect(
                self.ws_uri,
                extra_headers={"Authorization": f"Bearer {self.auth_token}"},
                ping_interval=30.0,
                ping_timeout=10.0
            )

            # Authenticate
            self.state = ConnectionState.AUTHENTICATING
            if not await self._authenticate():
                self.state = ConnectionState.FAILED
                return False

            # Start message handling
            self.state = ConnectionState.CONNECTED
            self.connection_task = asyncio.create_task(self._message_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info(f"Successfully connected to {self.remote_metadata.swarm_id}")

            if self.on_connected:
                try:
                    self.on_connected()
                except Exception as e:
                    logger.error(f"Error in connection callback: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.remote_metadata.swarm_id}: {e}")
            self.state = ConnectionState.FAILED
            return False

    async def disconnect(self):
        """Disconnect from the remote swarm."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from {self.remote_metadata.swarm_id}")
        self.state = ConnectionState.DISCONNECTED

        # Cancel tasks
        if self.connection_task and not self.connection_task.done():
            self.connection_task.cancel()
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()

        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")

        # Clean up pending responses
        for future in self.pending_responses.values():
            if not future.done():
                future.cancel()
        self.pending_responses.clear()

        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error(f"Error in disconnection callback: {e}")

    async def _authenticate(self) -> bool:
        """Perform authentication handshake."""
        if not self.websocket:
            return False

        try:
            # Send authentication message
            auth_message = FederationMessage(
                message_id=str(uuid.uuid4()),
                message_type="authenticate",
                sender_swarm_id=self.local_swarm_id,
                target_swarm_id=self.remote_metadata.swarm_id,
                payload={
                    "token": self.auth_token,
                    "capabilities": ["task_sharing", "memory_sync", "coordination"]
                },
                timestamp=asyncio.get_event_loop().time(),
                requires_response=True
            )

            await self.websocket.send(json.dumps(auth_message.to_dict()))

            # Wait for response with timeout
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=10.0
            )

            response_data = json.loads(response)
            response_msg = FederationMessage.from_dict(response_data)

            if response_msg.message_type == "auth_success":
                logger.info(f"Authentication successful with {self.remote_metadata.swarm_id}")
                return True
            else:
                logger.error(f"Authentication failed: {response_msg.payload.get('error', 'Unknown error')}")
                return False

        except asyncio.TimeoutError:
            logger.error("Authentication timeout")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def send_message(self,
                          message_type: str,
                          payload: Dict[str, Any],
                          requires_response: bool = False) -> Optional[FederationMessage]:
        """
        Send a message to the remote swarm.

        Args:
            message_type: Type of message
            payload: Message payload
            requires_response: Whether to wait for a response

        Returns:
            Response message if requires_response=True, None otherwise
        """
        if self.state != ConnectionState.CONNECTED or not self.websocket:
            logger.warning("Cannot send message: not connected")
            return None

        message = FederationMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_swarm_id=self.local_swarm_id,
            target_swarm_id=self.remote_metadata.swarm_id,
            payload=payload,
            timestamp=asyncio.get_event_loop().time(),
            requires_response=requires_response
        )

        try:
            await self.websocket.send(json.dumps(message.to_dict()))

            if requires_response:
                # Create future for response
                future = asyncio.Future()
                self.pending_responses[message.message_id] = future

                # Wait for response with timeout
                response = await asyncio.wait_for(future, timeout=30.0)
                return response
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def _message_loop(self):
        """Main loop for receiving and processing messages."""
        try:
            while self.state == ConnectionState.CONNECTED and self.websocket:
                try:
                    # Receive message
                    raw_message = await self.websocket.recv()
                    message_data = json.loads(raw_message)
                    message = FederationMessage.from_dict(message_data)

                    # Handle response messages
                    if message.message_id in self.pending_responses:
                        future = self.pending_responses.pop(message.message_id)
                        if not future.done():
                            future.set_result(message)
                        continue

                    # Handle regular messages
                    await self._handle_message(message)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"WebSocket connection closed for {self.remote_metadata.swarm_id}")
                    break
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON message")
                    continue
                except Exception as e:
                    logger.error(f"Error in message loop: {e}")
                    continue

        except asyncio.CancelledError:
            logger.debug("Message loop cancelled")
        except Exception as e:
            logger.error(f"Message loop error: {e}")
        finally:
            # Connection lost, trigger reconnection if not manually disconnected
            if self.state == ConnectionState.CONNECTED:
                self.state = ConnectionState.RECONNECTING
                asyncio.create_task(self._reconnect())

    async def _handle_message(self, message: FederationMessage):
        """Handle incoming message."""
        logger.debug(f"Received message: {message.message_type} from {message.sender_swarm_id}")

        # Call general message handler
        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

        # Call specific handler if registered
        if message.message_type in self.message_handlers:
            try:
                self.message_handlers[message.message_type](message)
            except Exception as e:
                logger.error(f"Error in message type handler: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        try:
            while self.state == ConnectionState.CONNECTED:
                await asyncio.sleep(self.heartbeat_interval)

                if self.state != ConnectionState.CONNECTED:
                    break

                # Send heartbeat
                await self.send_message("heartbeat", {"timestamp": asyncio.get_event_loop().time()})

        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

    async def _reconnect(self):
        """Attempt to reconnect after connection loss."""
        logger.info(f"Attempting to reconnect to {self.remote_metadata.swarm_id}")

        while self.state == ConnectionState.RECONNECTING:
            await asyncio.sleep(self.reconnect_interval)

            if self.state != ConnectionState.RECONNECTING:
                break

            logger.debug(f"Reconnecting to {self.remote_metadata.swarm_id}...")
            success = await self.connect()
            if success:
                break

        if self.state == ConnectionState.RECONNECTING:
            self.state = ConnectionState.FAILED
            logger.error(f"Failed to reconnect to {self.remote_metadata.swarm_id}")

    def register_message_handler(self, message_type: str, handler: Callable[[FederationMessage], None]):
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler

    def unregister_message_handler(self, message_type: str):
        """Unregister a message handler."""
        self.message_handlers.pop(message_type, None)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about the connection."""
        return {
            "remote_swarm_id": self.remote_metadata.swarm_id,
            "remote_host": self.remote_metadata.host,
            "remote_port": self.remote_metadata.api_port,
            "state": self.state.value,
            "ws_uri": self.ws_uri,
            "pending_responses": len(self.pending_responses)
        }


class FederationConnectionManager:
    """
    Manages multiple federation connections to different swarms.
    """

    def __init__(self, local_swarm_id: str, auth_token: str):
        """
        Initialize connection manager.

        Args:
            local_swarm_id: ID of the local swarm
            auth_token: Authentication token for federation
        """
        self.local_swarm_id = local_swarm_id
        self.auth_token = auth_token
        self.connections: Dict[str, FederationConnection] = {}

        # Callbacks
        self.on_connection_established: Optional[Callable[[str], None]] = None
        self.on_connection_lost: Optional[Callable[[str], None]] = None
        self.on_message_received: Optional[Callable[[str, FederationMessage], None]] = None

    async def connect_to_swarm(self, swarm_metadata: SwarmMetadata) -> bool:
        """
        Establish connection to a swarm.

        Args:
            swarm_metadata: Metadata of the swarm to connect to

        Returns:
            True if connection successful
        """
        if swarm_metadata.swarm_id in self.connections:
            logger.warning(f"Already connected to {swarm_metadata.swarm_id}")
            return True

        connection = FederationConnection(
            self.local_swarm_id,
            swarm_metadata,
            self.auth_token
        )

        # Set up callbacks
        connection.on_connected = lambda: self._on_connection_connected(swarm_metadata.swarm_id)
        connection.on_disconnected = lambda: self._on_connection_disconnected(swarm_metadata.swarm_id)
        connection.on_message = lambda msg: self._on_connection_message(swarm_metadata.swarm_id, msg)

        success = await connection.connect()
        if success:
            self.connections[swarm_metadata.swarm_id] = connection
            return True
        else:
            return False

    async def disconnect_from_swarm(self, swarm_id: str):
        """Disconnect from a specific swarm."""
        if swarm_id in self.connections:
            await self.connections[swarm_id].disconnect()
            del self.connections[swarm_id]

    async def broadcast_message(self,
                               message_type: str,
                               payload: Dict[str, Any],
                               requires_response: bool = False) -> Dict[str, Optional[FederationMessage]]:
        """
        Send message to all connected swarms.

        Returns:
            Dict mapping swarm_id to response (or None)
        """
        tasks = []
        for swarm_id, connection in self.connections.items():
            task = asyncio.create_task(
                connection.send_message(message_type, payload, requires_response)
            )
            tasks.append((swarm_id, task))

        results = {}
        for swarm_id, task in tasks:
            try:
                response = await task
                results[swarm_id] = response
            except Exception as e:
                logger.error(f"Failed to send to {swarm_id}: {e}")
                results[swarm_id] = None

        return results

    async def send_to_swarm(self,
                           swarm_id: str,
                           message_type: str,
                           payload: Dict[str, Any],
                           requires_response: bool = False) -> Optional[FederationMessage]:
        """Send message to a specific swarm."""
        if swarm_id not in self.connections:
            logger.warning(f"Not connected to {swarm_id}")
            return None

        return await self.connections[swarm_id].send_message(
            message_type, payload, requires_response
        )

    def _on_connection_connected(self, swarm_id: str):
        """Handle connection established."""
        logger.info(f"Federation connection established to {swarm_id}")
        if self.on_connection_established:
            try:
                self.on_connection_established(swarm_id)
            except Exception as e:
                logger.error(f"Error in connection established callback: {e}")

    def _on_connection_disconnected(self, swarm_id: str):
        """Handle connection lost."""
        logger.info(f"Federation connection lost to {swarm_id}")
        if swarm_id in self.connections:
            del self.connections[swarm_id]

        if self.on_connection_lost:
            try:
                self.on_connection_lost(swarm_id)
            except Exception as e:
                logger.error(f"Error in connection lost callback: {e}")

    def _on_connection_message(self, swarm_id: str, message: FederationMessage):
        """Handle incoming message."""
        if self.on_message_received:
            try:
                self.on_message_received(swarm_id, message)
            except Exception as e:
                logger.error(f"Error in message received callback: {e}")

    def get_connected_swarms(self) -> List[str]:
        """Get list of currently connected swarm IDs."""
        return list(self.connections.keys())

    def get_connection_info(self, swarm_id: str) -> Optional[Dict[str, Any]]:
        """Get connection info for a specific swarm."""
        if swarm_id in self.connections:
            return self.connections[swarm_id].get_connection_info()
        return None

    async def shutdown(self):
        """Shutdown all connections."""
        logger.info("Shutting down federation connections")
        tasks = [conn.disconnect() for conn in self.connections.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.connections.clear()