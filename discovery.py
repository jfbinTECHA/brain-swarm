"""
Discovery Layer for Brain Swarm Federation

This module implements UDP-based swarm discovery for multi-node Brain Swarm deployments.
It enables automatic discovery and registration of swarm nodes across a network.
"""

import socket
import threading
import time
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import hashlib
import uuid

# Optional imports for registry integration
try:
    from .registry_client import RegistryClient, RegistryManager
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    RegistryClient = None
    RegistryManager = None

logger = logging.getLogger(__name__)


@dataclass
class SwarmMetadata:
    """Metadata for a discovered swarm node."""
    swarm_id: str
    node_name: str
    host: str
    port: int
    api_port: int
    capabilities: List[str]
    agent_count: int
    last_seen: float
    status: str = "active"
    version: str = "1.0.0"
    federation_enabled: bool = True
    load_factor: float = 0.0
    unique_id: str = ""

    def __post_init__(self):
        if not self.unique_id:
            # Create a unique identifier based on swarm_id and host
            self.unique_id = hashlib.md5(f"{self.swarm_id}:{self.host}:{self.port}".encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwarmMetadata':
        return cls(**data)

    def is_expired(self, timeout: float = 300.0) -> bool:
        """Check if this swarm node has expired (not seen recently)."""
        return time.time() - self.last_seen > timeout

    def update_activity(self):
        """Update the last seen timestamp."""
        self.last_seen = time.time()


class DiscoveryLayer:
    """
    Hybrid discovery layer for Brain Swarm federation supporting both
    LAN UDP broadcasts and internet-wide registry-based discovery.

    This class handles:
    - Periodic UDP broadcasts announcing swarm presence (LAN)
    - Registry-based global discovery (internet-wide)
    - Listening for broadcasts from other swarms
    - Maintaining a local registry of discovered swarms
    - Health monitoring and cleanup of stale entries
    """

    def __init__(self,
                 swarm_id: str,
                 node_name: str,
                 broadcast_port: int = 9999,
                 api_port: int = 8000,
                 broadcast_interval: float = 30.0,
                 discovery_timeout: float = 300.0,
                 enable_registry: bool = False,
                 registry_url: Optional[str] = None,
                 registry_api_key: Optional[str] = None):
        """
        Initialize the discovery layer.

        Args:
            swarm_id: Unique identifier for this swarm
            node_name: Human-readable name for this node
            broadcast_port: UDP port for discovery broadcasts
            api_port: HTTP API port for this node
            broadcast_interval: Seconds between broadcast announcements
            discovery_timeout: Seconds before considering a node stale
            enable_registry: Enable registry-based global discovery
            registry_url: URL of the central registry service
            registry_api_key: API key for registry authentication
        """
        self.swarm_id = swarm_id
        self.node_name = node_name
        self.broadcast_port = broadcast_port
        self.api_port = api_port
        self.broadcast_interval = broadcast_interval
        self.discovery_timeout = discovery_timeout
        self.enable_registry = enable_registry and REGISTRY_AVAILABLE
        self.registry_url = registry_url
        self.registry_api_key = registry_api_key

        # Network setup
        self.broadcast_address = '<broadcast>'
        self.local_ip = self._get_local_ip()

        # Registry of discovered swarms
        self.discovered_swarms: Dict[str, SwarmMetadata] = {}
        self.own_metadata = self._create_own_metadata()

        # Threading
        self.broadcast_thread: Optional[threading.Thread] = None
        self.listen_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        self.registry_thread: Optional[threading.Thread] = None
        self.running = False

        # Registry integration
        self.registry_manager: Optional[RegistryManager] = None
        self.registry_discoveries: Dict[str, SwarmMetadata] = {}

        # Callbacks
        self.on_swarm_discovered: Optional[Callable[[SwarmMetadata], None]] = None
        self.on_swarm_lost: Optional[Callable[[SwarmMetadata], None]] = None

        # Socket setup
        self.broadcast_socket: Optional[socket.socket] = None
        self.listen_socket: Optional[socket.socket] = None

        # Log configuration
        discovery_modes = ["UDP broadcast"]
        if self.enable_registry:
            discovery_modes.append("registry")
        logger.info(f"Discovery layer initialized for swarm {swarm_id} on {self.local_ip}:{broadcast_port} (modes: {', '.join(discovery_modes)})")

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"

    def _create_own_metadata(self) -> SwarmMetadata:
        """Create metadata for this swarm node."""
        return SwarmMetadata(
            swarm_id=self.swarm_id,
            node_name=self.node_name,
            host=self.local_ip,
            port=self.broadcast_port,
            api_port=self.api_port,
            capabilities=["coordination", "task_execution", "memory_management"],
            agent_count=0,  # Will be updated dynamically
            last_seen=time.time(),
            status="active",
            federation_enabled=True,
            load_factor=0.0
        )

    def start(self):
        """Start the discovery layer."""
        if self.running:
            logger.warning("Discovery layer already running")
            return

        logger.info("Starting discovery layer...")
        self.running = True

        # Setup sockets for UDP broadcast
        self._setup_sockets()

        # Start UDP threads
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)

        self.broadcast_thread.start()
        self.listen_thread.start()
        self.cleanup_thread.start()

        # Start registry integration if enabled
        if self.enable_registry:
            self._start_registry_integration()

        logger.info("Discovery layer started successfully")

    def stop(self):
        """Stop the discovery layer."""
        if not self.running:
            logger.warning("Discovery layer not running")
            return

        logger.info("Stopping discovery layer...")
        self.running = False

        # Stop registry integration
        if self.registry_manager:
            asyncio.run(self.registry_manager.stop())
            self.registry_manager = None

        # Close sockets
        if self.broadcast_socket:
            self.broadcast_socket.close()
        if self.listen_socket:
            self.listen_socket.close()

        # Wait for threads to finish
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join(timeout=5.0)
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=5.0)
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        if self.registry_thread and self.registry_thread.is_alive():
            self.registry_thread.join(timeout=5.0)

        logger.info("Discovery layer stopped")

    def _setup_sockets(self):
        """Setup UDP sockets for broadcasting and listening."""
        try:
            # Broadcast socket
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Listen socket
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind(('', self.broadcast_port))

            logger.debug("UDP sockets configured successfully")

        except Exception as e:
            logger.error(f"Failed to setup sockets: {e}")
            raise

    def _broadcast_loop(self):
        """Main loop for broadcasting swarm presence."""
        logger.debug("Starting broadcast loop")

        while self.running:
            try:
                self._send_broadcast()
                time.sleep(self.broadcast_interval)
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                time.sleep(5.0)  # Wait before retrying

    def _send_broadcast(self):
        """Send a UDP broadcast announcing this swarm's presence."""
        if not self.broadcast_socket:
            return

        try:
            # Update own metadata with current status
            self.own_metadata.last_seen = time.time()

            # Create broadcast message
            message = {
                "type": "swarm_announcement",
                "timestamp": time.time(),
                "metadata": self.own_metadata.to_dict()
            }

            data = json.dumps(message).encode('utf-8')

            # Send broadcast
            self.broadcast_socket.sendto(data, (self.broadcast_address, self.broadcast_port))

            logger.debug(f"Broadcast sent: {self.swarm_id}")

        except Exception as e:
            logger.error(f"Failed to send broadcast: {e}")

    def _listen_loop(self):
        """Main loop for listening to broadcasts from other swarms."""
        logger.debug("Starting listen loop")

        while self.running:
            try:
                self._listen_for_broadcasts()
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                time.sleep(1.0)

    def _listen_for_broadcasts(self):
        """Listen for and process incoming broadcasts."""
        if not self.listen_socket:
            return

        try:
            # Set timeout for socket operations
            self.listen_socket.settimeout(1.0)

            while self.running:
                try:
                    data, addr = self.listen_socket.recvfrom(4096)
                    self._process_broadcast(data, addr)
                except socket.timeout:
                    continue  # Expected timeout, continue listening
                except OSError:
                    break  # Socket closed

        except Exception as e:
            logger.error(f"Error listening for broadcasts: {e}")

    def _process_broadcast(self, data: bytes, addr: tuple):
        """Process an incoming broadcast message."""
        try:
            message = json.loads(data.decode('utf-8'))

            if message.get("type") != "swarm_announcement":
                return  # Not a swarm announcement

            metadata_dict = message.get("metadata", {})
            if not metadata_dict:
                return

            # Create SwarmMetadata object
            metadata = SwarmMetadata.from_dict(metadata_dict)

            # Ignore our own broadcasts
            if metadata.unique_id == self.own_metadata.unique_id:
                return

            # Update or add to registry
            self._update_discovered_swarm(metadata)

        except json.JSONDecodeError:
            logger.debug("Received invalid JSON broadcast")
        except Exception as e:
            logger.error(f"Error processing broadcast: {e}")

    def _update_discovered_swarm(self, metadata: SwarmMetadata):
        """Update the registry with a discovered swarm."""
        swarm_key = metadata.unique_id
        is_new = swarm_key not in self.discovered_swarms

        # Update metadata
        metadata.update_activity()
        self.discovered_swarms[swarm_key] = metadata

        if is_new:
            logger.info(f"Discovered new swarm: {metadata.swarm_id} at {metadata.host}:{metadata.api_port}")
            if self.on_swarm_discovered:
                try:
                    self.on_swarm_discovered(metadata)
                except Exception as e:
                    logger.error(f"Error in swarm discovered callback: {e}")
        else:
            logger.debug(f"Updated existing swarm: {metadata.swarm_id}")

    def _cleanup_loop(self):
        """Periodic cleanup of stale swarm entries."""
        while self.running:
            try:
                self._cleanup_stale_swarms()
                time.sleep(60.0)  # Clean up every minute
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(10.0)

    def _cleanup_stale_swarms(self):
        """Remove swarms that haven't been seen recently."""
        current_time = time.time()
        stale_swarms = []

        for swarm_key, metadata in self.discovered_swarms.items():
            if metadata.is_expired(self.discovery_timeout):
                stale_swarms.append((swarm_key, metadata))

        for swarm_key, metadata in stale_swarms:
            logger.info(f"Removing stale swarm: {metadata.swarm_id}")
            del self.discovered_swarms[swarm_key]

            if self.on_swarm_lost:
                try:
                    self.on_swarm_lost(metadata)
                except Exception as e:
                    logger.error(f"Error in swarm lost callback: {e}")

    def get_discovered_swarms(self) -> List[SwarmMetadata]:
        """Get list of currently discovered swarms."""
        return list(self.discovered_swarms.values())

    def get_swarm_by_id(self, swarm_id: str) -> Optional[SwarmMetadata]:
        """Get a specific swarm by its swarm_id."""
        for metadata in self.discovered_swarms.values():
            if metadata.swarm_id == swarm_id:
                return metadata
        return None

    def update_own_status(self, agent_count: int = None, load_factor: float = None):
        """Update this node's status information."""
        if agent_count is not None:
            self.own_metadata.agent_count = agent_count
        if load_factor is not None:
            self.own_metadata.load_factor = load_factor

    def set_discovery_callbacks(self,
                               on_discovered: Callable[[SwarmMetadata], None] = None,
                               on_lost: Callable[[SwarmMetadata], None] = None):
        """Set callbacks for swarm discovery events."""
        self.on_swarm_discovered = on_discovered
        self.on_swarm_lost = on_lost

    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get statistics about the discovery layer."""
        stats = {
            "own_swarm_id": self.swarm_id,
            "own_node_name": self.node_name,
            "discovered_swarms_count": len(self.discovered_swarms),
            "broadcast_port": self.broadcast_port,
            "api_port": self.api_port,
            "broadcast_interval": self.broadcast_interval,
            "discovery_timeout": self.discovery_timeout,
            "is_running": self.running,
            "local_ip": self.local_ip,
            "discovery_modes": ["udp_broadcast"]
        }

        if self.enable_registry:
            stats["discovery_modes"].append("registry")
            stats["registry_enabled"] = True
            stats["registry_url"] = self.registry_url
            stats["registry_discoveries_count"] = len(self.registry_discoveries)

        return stats

    # Registry Integration Methods

    def _start_registry_integration(self):
        """Start registry-based discovery."""
        if not REGISTRY_AVAILABLE:
            logger.warning("Registry integration requested but registry_client not available")
            return

        if not self.registry_url or not self.registry_api_key:
            logger.warning("Registry integration enabled but URL/key not configured")
            return

        logger.info("Starting registry integration...")

        # Create registry manager
        self.registry_manager = RegistryManager(
            registry_url=self.registry_url,
            api_key=self.registry_api_key,
            swarm_id=self.swarm_id,
            node_name=self.node_name
        )

        # Set up callbacks
        self.registry_manager.on_swarm_discovered = self._on_registry_swarm_discovered

        # Start registry operations in background thread
        self.registry_thread = threading.Thread(target=self._registry_loop, daemon=True)
        self.registry_thread.start()

    def _registry_loop(self):
        """Main registry integration loop."""
        async def run_registry():
            try:
                # Start registry manager
                success = await self.registry_manager.start(
                    host=self.local_ip,
                    api_port=self.api_port,
                    discovery_port=self.broadcast_port,
                    capabilities=["communication", "task_sharing", "memory_sync"],
                    metadata={"discovery_modes": ["udp", "registry"]}
                )

                if success:
                    logger.info("Registry integration started successfully")

                    # Keep running and monitoring
                    while self.running:
                        await asyncio.sleep(30)  # Check every 30 seconds

                        # Trigger discovery update
                        try:
                            discoveries = await self.registry_manager.discover_swarms()
                            self._process_registry_discoveries(discoveries)
                        except Exception as e:
                            logger.error(f"Error in registry discovery: {e}")

                else:
                    logger.error("Failed to start registry integration")

            except Exception as e:
                logger.error(f"Registry loop error: {e}")

        # Run the async registry operations
        asyncio.run(run_registry())

    def _on_registry_swarm_discovered(self, swarm_data: Dict[str, Any]):
        """Handle swarm discovered via registry."""
        try:
            # Convert registry data to SwarmMetadata
            metadata = SwarmMetadata(
                swarm_id=swarm_data["swarm_id"],
                node_name=swarm_data["node_name"],
                host=swarm_data["host"],
                port=swarm_data["discovery_port"],
                api_port=swarm_data["api_port"],
                capabilities=swarm_data["capabilities"],
                agent_count=0,  # Not available from registry
                last_seen=time.time(),
                status=swarm_data.get("status", "active"),
                federation_enabled=swarm_data.get("federation_enabled", True),
                load_factor=0.0,  # Not available from registry
                unique_id=hashlib.md5(f"{swarm_data['swarm_id']}:{swarm_data['host']}:{swarm_data['port']}".encode()).hexdigest()[:8]
            )

            # Store in registry discoveries
            self.registry_discoveries[metadata.unique_id] = metadata

            # Add to main discoveries if not already there
            if metadata.unique_id not in self.discovered_swarms:
                self.discovered_swarms[metadata.unique_id] = metadata
                logger.info(f"Registry discovery: {metadata.swarm_id} at {metadata.host}:{metadata.api_port}")

                if self.on_swarm_discovered:
                    try:
                        self.on_swarm_discovered(metadata)
                    except Exception as e:
                        logger.error(f"Error in swarm discovered callback: {e}")

        except Exception as e:
            logger.error(f"Error processing registry discovery: {e}")

    def _process_registry_discoveries(self, discoveries: List[Dict[str, Any]]):
        """Process batch of registry discoveries."""
        current_registry_swarms = set()

        for swarm_data in discoveries:
            swarm_id = swarm_data["swarm_id"]
            unique_id = hashlib.md5(f"{swarm_id}:{swarm_data['host']}:{swarm_data['discovery_port']}".encode()).hexdigest()[:8]

            current_registry_swarms.add(unique_id)

            # Update or add
            if unique_id not in self.registry_discoveries:
                self._on_registry_swarm_discovered(swarm_data)
            else:
                # Update last seen
                self.registry_discoveries[unique_id].update_activity()

        # Check for lost swarms
        lost_swarms = []
        for unique_id, metadata in self.registry_discoveries.items():
            if unique_id not in current_registry_swarms:
                lost_swarms.append(metadata)

        for metadata in lost_swarms:
            unique_id = metadata.unique_id
            if unique_id in self.discovered_swarms:
                del self.discovered_swarms[unique_id]
            del self.registry_discoveries[unique_id]

            logger.info(f"Registry swarm lost: {metadata.swarm_id}")

            if self.on_swarm_lost:
                try:
                    self.on_swarm_lost(metadata)
                except Exception as e:
                    logger.error(f"Error in swarm lost callback: {e}")

    def enable_registry_discovery(self, registry_url: str, api_key: str):
        """
        Enable registry-based discovery.

        Args:
            registry_url: URL of the central registry
            api_key: API key for authentication
        """
        if not REGISTRY_AVAILABLE:
            logger.error("Registry discovery requested but registry_client not available")
            return

        self.enable_registry = True
        self.registry_url = registry_url
        self.registry_api_key = api_key

        if self.running:
            logger.info("Enabling registry discovery on running system")
            self._start_registry_integration()

    def disable_registry_discovery(self):
        """Disable registry-based discovery."""
        logger.info("Disabling registry discovery")
        self.enable_registry = False

        if self.registry_manager:
            asyncio.run(self.registry_manager.stop())
            self.registry_manager = None

        # Remove registry discoveries
        for unique_id in list(self.registry_discoveries.keys()):
            if unique_id in self.discovered_swarms:
                metadata = self.discovered_swarms[unique_id]
                del self.discovered_swarms[unique_id]

                if self.on_swarm_lost:
                    try:
                        self.on_swarm_lost(metadata)
                    except Exception as e:
                        logger.error(f"Error in swarm lost callback: {e}")

        self.registry_discoveries.clear()


# Convenience functions for easy usage

def create_discovery_layer(swarm_id: str,
                          node_name: str,
                          broadcast_port: int = 9999,
                          api_port: int = 8000) -> DiscoveryLayer:
    """Create and return a configured discovery layer."""
    return DiscoveryLayer(
        swarm_id=swarm_id,
        node_name=node_name,
        broadcast_port=broadcast_port,
        api_port=api_port
    )


def start_swarm_discovery(swarm_id: str,
                         node_name: str,
                         broadcast_port: int = 9999,
                         api_port: int = 8000) -> DiscoveryLayer:
    """Create and start a discovery layer for swarm federation."""
    discovery = create_discovery_layer(swarm_id, node_name, broadcast_port, api_port)
    discovery.start()
    return discovery