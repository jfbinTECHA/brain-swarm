#!/usr/bin/env python3
"""
Registry Client for Brain Swarm Global Discovery

A secure client library for Brain Swarm instances to interact with the
central federation registry for global discovery and coordination.

Features:
- Secure API key authentication
- Automatic swarm registration and heartbeat
- Swarm discovery and querying
- Connection health monitoring
- Rate limiting and retry logic
- TLS/HTTPS support
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable
import aiohttp
from aiohttp import ClientTimeout, ClientError
import secrets

logger = logging.getLogger(__name__)


class RegistryClient:
    """
    Client for interacting with the Brain Swarm Federation Registry.

    Provides secure communication with the central registry for swarm
    registration, discovery, and coordination across networks.
    """

    def __init__(self,
                 registry_url: str,
                 api_key: str,
                 swarm_id: str,
                 node_name: str = "local-node",
                 timeout: float = 30.0,
                 retry_attempts: int = 3,
                 heartbeat_interval: float = 60.0):
        """
        Initialize the registry client.

        Args:
            registry_url: Base URL of the registry service (e.g., "https://registry.example.com")
            api_key: API key for authentication
            swarm_id: Unique identifier for this swarm
            node_name: Human-readable node name
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
            heartbeat_interval: Interval between heartbeat updates in seconds
        """
        self.registry_url = registry_url.rstrip('/')
        self.api_key = api_key
        self.swarm_id = swarm_id
        self.node_name = node_name
        self.timeout = ClientTimeout(total=timeout)
        self.retry_attempts = retry_attempts
        self.heartbeat_interval = heartbeat_interval

        # Swarm metadata
        self.host: Optional[str] = None
        self.api_port: Optional[int] = None
        self.discovery_port: Optional[int] = None
        self.capabilities: List[str] = ["communication", "task_sharing"]
        self.federation_enabled: bool = True
        self.metadata: Dict[str, Any] = {}
        self.version: str = "1.0.0"

        # State
        self.registered = False
        self.last_heartbeat = 0
        self.session: Optional[aiohttp.ClientSession] = None

        # Callbacks
        self.on_registration_success: Optional[Callable[[], None]] = None
        self.on_registration_failure: Optional[Callable[[str], None]] = None
        self.on_discovery_update: Optional[Callable[[List[Dict[str, Any]]], None]] = None

        logger.info(f"Registry client initialized for swarm {swarm_id}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Establish connection to registry."""
        if self.session:
            return

        # Create HTTP session with authentication headers
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': f'BrainSwarm-RegistryClient/{self.version}'
        }

        # Configure connector with TLS settings
        connector = aiohttp.TCPConnector(
            limit=10,  # Connection pool limit
            limit_per_host=5,
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            verify_ssl=True  # Enable SSL verification
        )

        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=self.timeout,
            connector=connector
        )

        logger.info(f"Connected to registry at {self.registry_url}")

    async def disconnect(self):
        """Close connection to registry."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from registry")

    async def _make_request(self,
                           method: str,
                           endpoint: str,
                           data: Optional[Dict[str, Any]] = None,
                           params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make authenticated request to registry with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            Exception: If request fails after all retries
        """
        if not self.session:
            raise Exception("Not connected to registry")

        url = f"{self.registry_url}{endpoint}"

        for attempt in range(self.retry_attempts + 1):
            try:
                # Prepare request data
                json_data = json.dumps(data) if data else None

                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")

                async with self.session.request(
                    method=method,
                    url=url,
                    data=json_data,
                    params=params
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        return response_data
                    elif response.status == 401:
                        raise Exception("Authentication failed - invalid API key")
                    elif response.status == 403:
                        raise Exception("Authorization failed - insufficient permissions")
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"HTTP {response.status}: {response_data.get('detail', 'Unknown error')}")

            except (ClientError, asyncio.TimeoutError) as e:
                if attempt == self.retry_attempts:
                    raise Exception(f"Request failed after {self.retry_attempts + 1} attempts: {e}")
                else:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue

    def configure_swarm(self,
                        host: str,
                        api_port: int,
                        discovery_port: int,
                        capabilities: Optional[List[str]] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """
        Configure swarm metadata for registration.

        Args:
            host: Host address or IP
            api_port: API port for WebSocket connections
            discovery_port: Discovery port (UDP)
            capabilities: List of swarm capabilities
            metadata: Additional metadata
        """
        self.host = host
        self.api_port = api_port
        self.discovery_port = discovery_port

        if capabilities:
            self.capabilities = capabilities
        if metadata:
            self.metadata = metadata

        logger.info(f"Configured swarm: {host}:{api_port} (discovery: {discovery_port})")

    async def register(self) -> bool:
        """
        Register this swarm with the registry.

        Returns:
            True if registration successful, False otherwise
        """
        if not all([self.host, self.api_port, self.discovery_port]):
            raise Exception("Swarm not fully configured - call configure_swarm() first")

        registration_data = {
            "swarm_id": self.swarm_id,
            "node_name": self.node_name,
            "host": self.host,
            "api_port": self.api_port,
            "discovery_port": self.discovery_port,
            "capabilities": self.capabilities,
            "federation_enabled": self.federation_enabled,
            "metadata": self.metadata,
            "version": self.version
        }

        try:
            logger.info(f"Registering swarm {self.swarm_id} with registry...")
            response = await self._make_request("POST", "/swarms", registration_data)

            self.registered = True
            self.last_heartbeat = time.time()

            logger.info(f"Successfully registered swarm {self.swarm_id}")

            if self.on_registration_success:
                try:
                    self.on_registration_success()
                except Exception as e:
                    logger.error(f"Error in registration success callback: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to register swarm: {e}")

            if self.on_registration_failure:
                try:
                    self.on_registration_failure(str(e))
                except Exception as callback_error:
                    logger.error(f"Error in registration failure callback: {callback_error}")

            return False

    async def unregister(self) -> bool:
        """
        Unregister this swarm from the registry.

        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            logger.info(f"Unregistering swarm {self.swarm_id}...")
            await self._make_request("DELETE", f"/swarms/{self.swarm_id}")

            self.registered = False
            logger.info(f"Successfully unregistered swarm {self.swarm_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister swarm: {e}")
            return False

    async def heartbeat(self) -> bool:
        """
        Send heartbeat to registry to indicate swarm is still active.

        Returns:
            True if heartbeat successful, False otherwise
        """
        if not self.registered:
            logger.warning("Cannot send heartbeat - swarm not registered")
            return False

        try:
            await self._make_request("POST", f"/swarms/{self.swarm_id}/heartbeat")
            self.last_heartbeat = time.time()
            return True

        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False

    async def discover_swarms(self,
                              capability: Optional[str] = None,
                              federation_enabled: Optional[bool] = None,
                              status: str = "active") -> List[Dict[str, Any]]:
        """
        Discover other registered swarms.

        Args:
            capability: Filter by specific capability
            federation_enabled: Filter by federation participation
            status: Filter by swarm status

        Returns:
            List of discovered swarm registrations
        """
        try:
            params = {}
            if capability:
                params["capability"] = capability
            if federation_enabled is not None:
                params["federation_enabled"] = str(federation_enabled).lower()
            if status:
                params["status"] = status

            response = await self._make_request("GET", "/swarms", params=params)
            swarms = response.get("swarms", [])

            logger.info(f"Discovered {len(swarms)} swarms")

            if self.on_discovery_update:
                try:
                    self.on_discovery_update(swarms)
                except Exception as e:
                    logger.error(f"Error in discovery update callback: {e}")

            return swarms

        except Exception as e:
            logger.error(f"Failed to discover swarms: {e}")
            return []

    async def get_swarm(self, swarm_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific swarm.

        Args:
            swarm_id: ID of the swarm to query

        Returns:
            Swarm registration data or None if not found
        """
        try:
            response = await self._make_request("GET", f"/swarms/{swarm_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to get swarm {swarm_id}: {e}")
            return None

    async def start_heartbeat_loop(self):
        """Start periodic heartbeat loop."""
        logger.info(f"Starting heartbeat loop (interval: {self.heartbeat_interval}s)")

        while self.registered:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if not self.registered:
                    break

                success = await self.heartbeat()
                if not success:
                    logger.warning("Heartbeat failed - swarm may be marked as inactive")

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def monitor_discovery(self, interval: float = 30.0):
        """
        Continuously monitor for new swarm discoveries.

        Args:
            interval: Polling interval in seconds
        """
        logger.info(f"Starting discovery monitoring (interval: {interval}s)")

        last_discovery = []

        while self.registered:
            try:
                await asyncio.sleep(interval)

                if not self.registered:
                    break

                current_discovery = await self.discover_swarms()

                # Check for changes
                if len(current_discovery) != len(last_discovery):
                    logger.info(f"Discovery changed: {len(last_discovery)} -> {len(current_discovery)} swarms")
                    last_discovery = current_discovery

            except asyncio.CancelledError:
                logger.info("Discovery monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in discovery monitoring: {e}")
                await asyncio.sleep(5)

    def get_status(self) -> Dict[str, Any]:
        """Get client status information."""
        return {
            "swarm_id": self.swarm_id,
            "node_name": self.node_name,
            "registered": self.registered,
            "registry_url": self.registry_url,
            "last_heartbeat": self.last_heartbeat,
            "configured": all([self.host, self.api_port, self.discovery_port]),
            "host": self.host,
            "api_port": self.api_port,
            "discovery_port": self.discovery_port,
            "capabilities": self.capabilities,
            "federation_enabled": self.federation_enabled
        }


class RegistryManager:
    """
    High-level manager for registry operations with automatic lifecycle management.
    """

    def __init__(self,
                 registry_url: str,
                 api_key: str,
                 swarm_id: str,
                 node_name: str = "local-node"):
        self.registry_url = registry_url
        self.api_key = api_key
        self.swarm_id = swarm_id
        self.node_name = node_name

        self.client: Optional[RegistryClient] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_swarm_discovered: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_swarm_lost: Optional[Callable[[str], None]] = None

    async def start(self,
                   host: str,
                   api_port: int,
                   discovery_port: int,
                   capabilities: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start registry operations.

        Args:
            host: Local host address
            api_port: Local API port
            discovery_port: Local discovery port
            capabilities: Swarm capabilities
            metadata: Additional metadata

        Returns:
            True if successfully started
        """
        try:
            # Create and configure client
            self.client = RegistryClient(
                registry_url=self.registry_url,
                api_key=self.api_key,
                swarm_id=self.swarm_id,
                node_name=self.node_name
            )

            self.client.configure_swarm(
                host=host,
                api_port=api_port,
                discovery_port=discovery_port,
                capabilities=capabilities,
                metadata=metadata
            )

            # Set up callbacks
            self.client.on_discovery_update = self._handle_discovery_update

            # Connect and register
            await self.client.connect()
            success = await self.client.register()

            if success:
                # Start background tasks
                self.heartbeat_task = asyncio.create_task(self.client.start_heartbeat_loop())
                self.monitor_task = asyncio.create_task(self.client.monitor_discovery())

                logger.info(f"Registry manager started for swarm {self.swarm_id}")
                return True
            else:
                await self.client.disconnect()
                return False

        except Exception as e:
            logger.error(f"Failed to start registry manager: {e}")
            return False

    async def stop(self):
        """Stop registry operations."""
        try:
            # Cancel background tasks
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()

            # Unregister and disconnect
            if self.client:
                await self.client.unregister()
                await self.client.disconnect()

            logger.info(f"Registry manager stopped for swarm {self.swarm_id}")

        except Exception as e:
            logger.error(f"Error stopping registry manager: {e}")

    def _handle_discovery_update(self, swarms: List[Dict[str, Any]]):
        """Handle discovery updates."""
        # This would compare with previous discoveries to detect new/lost swarms
        if self.on_swarm_discovered:
            for swarm in swarms:
                try:
                    self.on_swarm_discovered(swarm)
                except Exception as e:
                    logger.error(f"Error in swarm discovered callback: {e}")

    async def discover_swarms(self, **filters) -> List[Dict[str, Any]]:
        """Discover swarms with optional filters."""
        if not self.client:
            return []
        return await self.client.discover_swarms(**filters)

    def get_status(self) -> Dict[str, Any]:
        """Get registry manager status."""
        if not self.client:
            return {"status": "not_started"}

        return {
            "status": "active" if self.client.registered else "inactive",
            "client_status": self.client.get_status(),
            "heartbeat_active": self.heartbeat_task and not self.heartbeat_task.done(),
            "monitor_active": self.monitor_task and not self.monitor_task.done()
        }


# Utility functions
def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def validate_registry_url(url: str) -> bool:
    """Validate registry URL format."""
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create registry manager
        manager = RegistryManager(
            registry_url="http://localhost:8001",
            api_key="your-api-key-here",
            swarm_id="example-swarm",
            node_name="example-node"
        )

        # Set up callbacks
        def on_swarm_discovered(swarm):
            print(f"Discovered swarm: {swarm['swarm_id']} at {swarm['host']}:{swarm['api_port']}")

        manager.on_swarm_discovered = on_swarm_discovered

        # Start registry operations
        success = await manager.start(
            host="192.168.1.100",
            api_port=8000,
            discovery_port=9999,
            capabilities=["communication", "task_sharing", "memory_sync"]
        )

        if success:
            print("Registry manager started successfully")

            # Keep running for a while
            await asyncio.sleep(60)

            # Discover swarms
            swarms = await manager.discover_swarms()
            print(f"Found {len(swarms)} swarms")

        # Stop
        await manager.stop()

    asyncio.run(main())