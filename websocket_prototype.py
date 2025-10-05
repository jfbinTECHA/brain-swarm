#!/usr/bin/env python3
"""
WebSocket Connection Prototype for Brain Swarm Federation

A simple standalone prototype for testing WebSocket-based communication between swarm nodes.
This prototype demonstrates the connection and message exchange mechanism used by the federation.

Usage:
    # Terminal 1: Start a server
    python websocket_prototype.py server

    # Terminal 2: Start a client and connect
    python websocket_prototype.py client --server localhost:8765

    # Terminal 3: Start another client
    python websocket_prototype.py client --server localhost:8765 --swarm-id swarm-2
"""

import asyncio
import json
import logging
import argparse
import sys
import uuid
from typing import Dict, Any, Optional, Set
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SwarmWebSocketServer:
    """Simple WebSocket server for swarm communication."""

    def __init__(self, host: str = "localhost", port: int = 8765, swarm_id: str = "server-swarm"):
        self.host = host
        self.port = port
        self.swarm_id = swarm_id
        self.server: Optional[websockets.WebSocketServer] = None
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_info: Dict[websockets.WebSocketServerProtocol, Dict[str, Any]] = {}

        logger.info(f"WebSocket server initialized: {swarm_id} on {host}:{port}")

    async def start(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30.0,
                ping_timeout=10.0
            )

            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

            # Keep server running
            await self.server.wait_closed()

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle a client connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_id}")

        # Add to connected clients
        self.connected_clients.add(websocket)
        self.client_info[websocket] = {
            "id": client_id,
            "connected_at": asyncio.get_event_loop().time(),
            "swarm_id": None
        }

        try:
            # Handle authentication
            await self.handle_authentication(websocket)

            # Main message loop
            async for message in websocket:
                await self.handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up
            self.connected_clients.discard(websocket)
            self.client_info.pop(websocket, None)

    async def handle_authentication(self, websocket: websockets.WebSocketServerProtocol):
        """Handle client authentication."""
        try:
            # Wait for authentication message with timeout
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_message)

            if auth_data.get("type") == "authenticate":
                # Simple authentication - accept any client
                swarm_id = auth_data.get("swarm_id", "unknown")
                self.client_info[websocket]["swarm_id"] = swarm_id

                # Send success response
                response = {
                    "type": "auth_success",
                    "server_swarm_id": self.swarm_id,
                    "message": "Authentication successful",
                    "timestamp": asyncio.get_event_loop().time()
                }

                await websocket.send(json.dumps(response))
                logger.info(f"Client authenticated: {swarm_id} from {self.client_info[websocket]['id']}")
            else:
                # Invalid auth message
                response = {
                    "type": "auth_failed",
                    "error": "Invalid authentication message",
                    "timestamp": asyncio.get_event_loop().time()
                }
                await websocket.send(json.dumps(response))
                await websocket.close()

        except asyncio.TimeoutError:
            logger.warning(f"Authentication timeout for {self.client_info[websocket]['id']}")
            await websocket.close()
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await websocket.close()

    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            client_info = self.client_info.get(websocket, {})

            logger.info(f"Received {msg_type} from {client_info.get('swarm_id', 'unknown')}")

            # Handle different message types
            if msg_type == "ping":
                await self.handle_ping(websocket, data)
            elif msg_type == "task_request":
                await self.handle_task_request(websocket, data)
            elif msg_type == "status_update":
                await self.handle_status_update(websocket, data)
            elif msg_type == "broadcast":
                await self.handle_broadcast(websocket, data)
            else:
                # Echo unknown messages back
                response = {
                    "type": "echo",
                    "original_type": msg_type,
                    "received_at": asyncio.get_event_loop().time(),
                    "data": data
                }
                await websocket.send(json.dumps(response))

        except json.JSONDecodeError:
            logger.warning("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_ping(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle ping message."""
        response = {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time(),
            "server_swarm_id": self.swarm_id
        }
        await websocket.send(json.dumps(response))

    async def handle_task_request(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle task request."""
        # Simulate task availability
        available_tasks = [
            {
                "task_id": f"task_{uuid.uuid4().hex[:8]}",
                "type": "computation",
                "priority": 1,
                "description": "Sample computational task"
            },
            {
                "task_id": f"task_{uuid.uuid4().hex[:8]}",
                "type": "analysis",
                "priority": 2,
                "description": "Data analysis task"
            }
        ]

        response = {
            "type": "task_response",
            "available_tasks": available_tasks,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(response))

    async def handle_status_update(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle status update."""
        client_info = self.client_info.get(websocket, {})
        swarm_id = client_info.get("swarm_id", "unknown")

        # Store status info
        client_info["last_status"] = data
        client_info["last_status_time"] = asyncio.get_event_loop().time()

        logger.info(f"Status update from {swarm_id}: {data.get('status', 'unknown')}")

        # Acknowledge
        response = {
            "type": "status_ack",
            "received": True,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(response))

    async def handle_broadcast(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle broadcast request - send to all other clients."""
        sender_info = self.client_info.get(websocket, {})
        sender_swarm = sender_info.get("swarm_id", "unknown")

        # Prepare broadcast message
        broadcast_msg = {
            "type": "federation_broadcast",
            "from_swarm": sender_swarm,
            "original_data": data,
            "timestamp": asyncio.get_event_loop().time()
        }

        # Send to all other connected clients
        sent_count = 0
        for client in self.connected_clients:
            if client != websocket:  # Don't send back to sender
                try:
                    await client.send(json.dumps(broadcast_msg))
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to client: {e}")

        logger.info(f"Broadcast from {sender_swarm} sent to {sent_count} clients")

        # Confirm to sender
        response = {
            "type": "broadcast_ack",
            "recipients": sent_count,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(response))

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            "swarm_id": self.swarm_id,
            "connected_clients": len(self.connected_clients),
            "client_details": [
                {
                    "id": info["id"],
                    "swarm_id": info.get("swarm_id"),
                    "connected_for": asyncio.get_event_loop().time() - info["connected_at"]
                }
                for info in self.client_info.values()
            ],
            "host": self.host,
            "port": self.port
        }


class SwarmWebSocketClient:
    """Simple WebSocket client for swarm communication."""

    def __init__(self, server_uri: str, swarm_id: str = "client-swarm", node_name: str = "client-node"):
        self.server_uri = server_uri
        self.swarm_id = swarm_id
        self.node_name = node_name
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.message_handlers: Dict[str, callable] = {}

        # Set up default message handlers
        self.setup_default_handlers()

        logger.info(f"WebSocket client initialized: {swarm_id} connecting to {server_uri}")

    def setup_default_handlers(self):
        """Setup default message handlers."""
        self.message_handlers = {
            "auth_success": self.handle_auth_success,
            "auth_failed": self.handle_auth_failed,
            "pong": self.handle_pong,
            "task_response": self.handle_task_response,
            "status_ack": self.handle_status_ack,
            "broadcast_ack": self.handle_broadcast_ack,
            "federation_broadcast": self.handle_federation_broadcast,
            "echo": self.handle_echo
        }

    async def connect(self) -> bool:
        """Connect to the server."""
        try:
            logger.info(f"Connecting to {self.server_uri}...")
            self.websocket = await websockets.connect(
                self.server_uri,
                ping_interval=30.0,
                ping_timeout=10.0
            )

            # Authenticate
            await self.authenticate()

            # Start message handling
            asyncio.create_task(self.message_loop())

            self.connected = True
            logger.info(f"Successfully connected as {self.swarm_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def authenticate(self):
        """Send authentication message."""
        auth_msg = {
            "type": "authenticate",
            "swarm_id": self.swarm_id,
            "node_name": self.node_name,
            "capabilities": ["communication", "task_sharing"],
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.websocket.send(json.dumps(auth_msg))
        logger.info("Authentication message sent")

    async def message_loop(self):
        """Main message handling loop."""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
        except Exception as e:
            logger.error(f"Error in message loop: {e}")
        finally:
            self.connected = False

    async def handle_message(self, message: str):
        """Handle incoming message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")

            logger.info(f"Received {msg_type} message")

            # Call appropriate handler
            if msg_type in self.message_handlers:
                await self.message_handlers[msg_type](data)
            else:
                logger.warning(f"No handler for message type: {msg_type}")

        except json.JSONDecodeError:
            logger.warning("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    # Message handlers

    async def handle_auth_success(self, data: Dict[str, Any]):
        """Handle authentication success."""
        server_swarm = data.get("server_swarm_id", "unknown")
        logger.info(f"Authentication successful with server swarm: {server_swarm}")

    async def handle_auth_failed(self, data: Dict[str, Any]):
        """Handle authentication failure."""
        error = data.get("error", "Unknown error")
        logger.error(f"Authentication failed: {error}")

    async def handle_pong(self, data: Dict[str, Any]):
        """Handle pong response."""
        server_swarm = data.get("server_swarm_id", "unknown")
        logger.debug(f"Pong from {server_swarm}")

    async def handle_task_response(self, data: Dict[str, Any]):
        """Handle task response."""
        tasks = data.get("available_tasks", [])
        logger.info(f"Received {len(tasks)} available tasks")
        for task in tasks:
            logger.info(f"  - {task['task_id']}: {task['description']}")

    async def handle_status_ack(self, data: Dict[str, Any]):
        """Handle status acknowledgment."""
        logger.info("Status update acknowledged")

    async def handle_broadcast_ack(self, data: Dict[str, Any]):
        """Handle broadcast acknowledgment."""
        recipients = data.get("recipients", 0)
        logger.info(f"Broadcast sent to {recipients} recipients")

    async def handle_federation_broadcast(self, data: Dict[str, Any]):
        """Handle federation broadcast."""
        from_swarm = data.get("from_swarm", "unknown")
        logger.info(f"Federation broadcast received from {from_swarm}")

    async def handle_echo(self, data: Dict[str, Any]):
        """Handle echo response."""
        original_type = data.get("original_type", "unknown")
        logger.info(f"Echo response for {original_type}")

    # Client actions

    async def send_ping(self):
        """Send ping message."""
        if not self.connected or not self.websocket:
            logger.warning("Not connected")
            return

        ping_msg = {
            "type": "ping",
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.websocket.send(json.dumps(ping_msg))
        logger.info("Ping sent")

    async def request_tasks(self):
        """Request available tasks."""
        if not self.connected or not self.websocket:
            logger.warning("Not connected")
            return

        task_msg = {
            "type": "task_request",
            "requirements": {"priority": "any"},
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.websocket.send(json.dumps(task_msg))
        logger.info("Task request sent")

    async def send_status_update(self, status: str = "active"):
        """Send status update."""
        if not self.connected or not self.websocket:
            logger.warning("Not connected")
            return

        status_msg = {
            "type": "status_update",
            "status": status,
            "load_factor": 0.5,
            "active_tasks": 2,
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.websocket.send(json.dumps(status_msg))
        logger.info(f"Status update sent: {status}")

    async def send_broadcast(self, message: str = "Hello federation!"):
        """Send broadcast message."""
        if not self.connected or not self.websocket:
            logger.warning("Not connected")
            return

        broadcast_msg = {
            "type": "broadcast",
            "message": message,
            "from_swarm": self.swarm_id,
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.websocket.send(json.dumps(broadcast_msg))
        logger.info("Broadcast message sent")

    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
        self.connected = False
        logger.info("Disconnected from server")


async def run_server(host: str, port: int, swarm_id: str):
    """Run WebSocket server."""
    server = SwarmWebSocketServer(host, port, swarm_id)
    await server.start()


async def run_client(server_uri: str, swarm_id: str, interactive: bool = True):
    """Run WebSocket client."""
    client = SwarmWebSocketClient(server_uri, swarm_id)

    if not await client.connect():
        return

    if interactive:
        # Interactive mode
        print("\nWebSocket Client Commands:")
        print("  ping          - Send ping")
        print("  tasks         - Request tasks")
        print("  status        - Send status update")
        print("  broadcast     - Send broadcast message")
        print("  quit          - Disconnect and quit")
        print()

        while client.connected:
            try:
                cmd = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
                cmd = cmd.strip().lower()

                if cmd == "ping":
                    await client.send_ping()
                elif cmd == "tasks":
                    await client.request_tasks()
                elif cmd == "status":
                    await client.send_status_update()
                elif cmd == "broadcast":
                    await client.send_broadcast()
                elif cmd == "quit":
                    await client.disconnect()
                    break
                else:
                    print("Unknown command. Type 'help' for commands.")

            except KeyboardInterrupt:
                await client.disconnect()
                break
            except Exception as e:
                logger.error(f"Command error: {e}")

    else:
        # Demo mode - send some messages automatically
        await asyncio.sleep(2)
        await client.send_ping()
        await asyncio.sleep(2)
        await client.request_tasks()
        await asyncio.sleep(2)
        await client.send_status_update()
        await asyncio.sleep(2)
        await client.send_broadcast()

        # Keep connected for a while
        await asyncio.sleep(30)


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="WebSocket Connection Prototype for Brain Swarm Federation")
    parser.add_argument("mode", choices=["server", "client"],
                       help="Mode: server or client")
    parser.add_argument("--host", default="localhost",
                       help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765,
                       help="Server port (default: 8765)")
    parser.add_argument("--server", help="Server URI for client (e.g., ws://localhost:8765)")
    parser.add_argument("--swarm-id", default="test-swarm",
                       help="Swarm ID (default: test-swarm)")
    parser.add_argument("--node-name", default="test-node",
                       help="Node name (default: test-node)")
    parser.add_argument("--interactive", action="store_true",
                       help="Enable interactive client mode")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.mode == "server":
            host = args.host
            port = args.port
            swarm_id = args.swarm_id

            logger.info(f"Starting WebSocket server: {swarm_id} on {host}:{port}")
            asyncio.run(run_server(host, port, swarm_id))

        elif args.mode == "client":
            if not args.server:
                # Auto-construct server URI
                server_uri = f"ws://{args.host}:{args.port}"
            else:
                server_uri = args.server

            swarm_id = args.swarm_id
            interactive = args.interactive

            logger.info(f"Starting WebSocket client: {swarm_id} connecting to {server_uri}")
            asyncio.run(run_client(server_uri, swarm_id, interactive))

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()