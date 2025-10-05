"""
Federation Manager Extension for Brain Swarm

Integrates discovery and connection layers to enable cross-swarm communication,
task sharing, memory synchronization, and analytics distribution.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import time

from ..discovery import DiscoveryLayer, SwarmMetadata
from ..federation_connection import FederationConnectionManager, FederationMessage

# Optional imports - handle gracefully if not available
try:
    from ..memory import WorkingMemory, LongTermMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

try:
    from ..analytics import predictive_analytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SharedTask:
    """Represents a task that can be shared across swarms."""
    task_id: str
    task_type: str
    priority: int
    payload: Dict[str, Any]
    origin_swarm: str
    created_at: float
    assigned_to: Optional[str] = None
    status: str = "pending"


@dataclass
class MemorySync:
    """Represents memory information for synchronization."""
    memory_type: str
    key: str
    value: Any
    origin_swarm: str
    timestamp: float
    ttl: Optional[float] = None


@dataclass
class AnalyticsData:
    """Represents analytics data for sharing."""
    data_type: str
    metrics: Dict[str, Any]
    origin_swarm: str
    time_range: tuple[float, float]
    timestamp: float


class FederationManager:
    """
    Extended federation manager that integrates discovery and connection layers
    to enable sharing of tasks, memory, and analytics across swarms.
    """

    def __init__(self,
                 local_swarm_id: str,
                 auth_token: str,
                 discovery_layer: Optional[DiscoveryLayer] = None):
        """
        Initialize the federation manager.

        Args:
            local_swarm_id: ID of the local swarm
            auth_token: Authentication token for federation connections
            discovery_layer: Optional discovery layer instance
        """
        self.local_swarm_id = local_swarm_id
        self.auth_token = auth_token

        # Core components
        self.discovery_layer = discovery_layer
        self.connection_manager = FederationConnectionManager(local_swarm_id, auth_token)

        # Data managers (to be injected)
        self.memory_manager: Optional[Any] = None  # WorkingMemory or LongTermMemory
        self.analytics_manager: Optional[Any] = None  # Analytics predictors
        self.task_manager: Optional[Any] = None

        # Federation state
        self.shared_tasks: Dict[str, SharedTask] = {}
        self.memory_cache: Dict[str, MemorySync] = {}
        self.analytics_cache: Dict[str, AnalyticsData] = {}

        # Callbacks
        self.on_task_received: Optional[Callable[[SharedTask], None]] = None
        self.on_memory_update: Optional[Callable[[MemorySync], None]] = None
        self.on_analytics_received: Optional[Callable[[AnalyticsData], None]] = None

        # Setup connection manager callbacks
        self._setup_connection_callbacks()

        logger.info(f"Federation manager initialized for swarm {local_swarm_id}")

    def _setup_connection_callbacks(self):
        """Setup callbacks for connection manager events."""
        self.connection_manager.on_connection_established = self._on_connection_established
        self.connection_manager.on_connection_lost = self._on_connection_lost
        self.connection_manager.on_message_received = self._on_message_received

    def _on_connection_established(self, swarm_id: str):
        """Handle new connection established."""
        logger.info(f"Federation connection established to {swarm_id}")
        # Could trigger initial sync or announcements

    def _on_connection_lost(self, swarm_id: str):
        """Handle connection lost."""
        logger.info(f"Federation connection lost to {swarm_id}")
        # Could trigger failover or redistribution of tasks

    def _on_message_received(self, swarm_id: str, message: FederationMessage):
        """Handle incoming federation message."""
        try:
            if message.message_type == "task_share":
                self._handle_task_share(message)
            elif message.message_type == "memory_sync":
                self._handle_memory_sync(message)
            elif message.message_type == "analytics_share":
                self._handle_analytics_share(message)
            elif message.message_type == "task_request":
                self._handle_task_request(message)
            elif message.message_type == "resource_request":
                self._handle_resource_request(message)
            else:
                logger.debug(f"Unknown message type: {message.message_type}")
        except Exception as e:
            logger.error(f"Error handling message from {swarm_id}: {e}")

    async def start_federation(self):
        """Start the federation by connecting to discovered swarms."""
        if not self.discovery_layer:
            logger.warning("No discovery layer configured")
            return

        logger.info("Starting federation connections...")

        # Get discovered swarms
        discovered_swarms = self.discovery_layer.get_discovered_swarms()

        # Connect to each discovered swarm
        for swarm in discovered_swarms:
            if swarm.swarm_id != self.local_swarm_id:  # Don't connect to self
                await self.connection_manager.connect_to_swarm(swarm)

        logger.info(f"Federation started with {len(self.connection_manager.get_connected_swarms())} connections")

    async def stop_federation(self):
        """Stop all federation connections."""
        logger.info("Stopping federation...")
        await self.connection_manager.shutdown()
        logger.info("Federation stopped")

    # Task Sharing Methods

    async def share_task(self, task: SharedTask, target_swarms: Optional[List[str]] = None) -> bool:
        """
        Share a task with connected swarms.

        Args:
            task: The task to share
            target_swarms: Specific swarms to share with, or None for all

        Returns:
            True if sharing was successful
        """
        message = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "priority": task.priority,
            "payload": task.payload,
            "origin_swarm": task.origin_swarm,
            "created_at": task.created_at,
            "status": task.status
        }

        if target_swarms:
            # Send to specific swarms
            for swarm_id in target_swarms:
                await self.connection_manager.send_to_swarm(swarm_id, "task_share", message)
        else:
            # Broadcast to all
            await self.connection_manager.broadcast_message("task_share", message)

        # Store locally
        self.shared_tasks[task.task_id] = task
        return True

    def _handle_task_share(self, message: FederationMessage):
        """Handle incoming task share message."""
        try:
            task_data = message.payload
            task = SharedTask(**task_data)

            # Store the shared task
            self.shared_tasks[task.task_id] = task

            # Notify callback
            if self.on_task_received:
                try:
                    self.on_task_received(task)
                except Exception as e:
                    logger.error(f"Error in task received callback: {e}")

            logger.info(f"Received shared task {task.task_id} from {message.sender_swarm_id}")

        except Exception as e:
            logger.error(f"Error processing task share: {e}")

    async def request_task_distribution(self, task_requirements: Dict[str, Any]) -> List[SharedTask]:
        """
        Request task distribution from connected swarms.

        Args:
            task_requirements: Requirements for the task distribution

        Returns:
            List of tasks that can be distributed
        """
        responses = await self.connection_manager.broadcast_message(
            "task_request",
            {"requirements": task_requirements},
            requires_response=True
        )

        available_tasks = []
        for swarm_id, response in responses.items():
            if response and response.payload.get("available_tasks"):
                for task_data in response.payload["available_tasks"]:
                    task = SharedTask(**task_data)
                    available_tasks.append(task)

        return available_tasks

    def _handle_task_request(self, message: FederationMessage):
        """Handle incoming task request."""
        # This would typically check local task queue and respond with available tasks
        # For now, just acknowledge
        pass

    # Memory Sharing Methods

    async def share_memory(self, memory_sync: MemorySync, target_swarms: Optional[List[str]] = None):
        """
        Share memory information with connected swarms.

        Args:
            memory_sync: Memory data to share
            target_swarms: Specific swarms to share with, or None for all
        """
        message = {
            "memory_type": memory_sync.memory_type,
            "key": memory_sync.key,
            "value": memory_sync.value,
            "origin_swarm": memory_sync.origin_swarm,
            "timestamp": memory_sync.timestamp,
            "ttl": memory_sync.ttl
        }

        if target_swarms:
            for swarm_id in target_swarms:
                await self.connection_manager.send_to_swarm(swarm_id, "memory_sync", message)
        else:
            await self.connection_manager.broadcast_message("memory_sync", message)

        # Cache locally
        cache_key = f"{memory_sync.memory_type}:{memory_sync.key}"
        self.memory_cache[cache_key] = memory_sync

    def _handle_memory_sync(self, message: FederationMessage):
        """Handle incoming memory sync message."""
        try:
            memory_data = message.payload
            memory_sync = MemorySync(**memory_data)

            # Store in local cache
            cache_key = f"{memory_sync.memory_type}:{memory_sync.key}"
            self.memory_cache[cache_key] = memory_sync

            # Notify callback
            if self.on_memory_update:
                try:
                    self.on_memory_update(memory_sync)
                except Exception as e:
                    logger.error(f"Error in memory update callback: {e}")

            logger.debug(f"Received memory sync for {cache_key} from {message.sender_swarm_id}")

        except Exception as e:
            logger.error(f"Error processing memory sync: {e}")

    # Analytics Sharing Methods

    async def share_analytics(self, analytics_data: AnalyticsData, target_swarms: Optional[List[str]] = None):
        """
        Share analytics data with connected swarms.

        Args:
            analytics_data: Analytics data to share
            target_swarms: Specific swarms to share with, or None for all
        """
        message = {
            "data_type": analytics_data.data_type,
            "metrics": analytics_data.metrics,
            "origin_swarm": analytics_data.origin_swarm,
            "time_range": analytics_data.time_range,
            "timestamp": analytics_data.timestamp
        }

        if target_swarms:
            for swarm_id in target_swarms:
                await self.connection_manager.send_to_swarm(swarm_id, "analytics_share", message)
        else:
            await self.connection_manager.broadcast_message("analytics_share", message)

        # Cache locally
        cache_key = f"{analytics_data.data_type}:{analytics_data.origin_swarm}:{analytics_data.timestamp}"
        self.analytics_cache[cache_key] = analytics_data

    def _handle_analytics_share(self, message: FederationMessage):
        """Handle incoming analytics share message."""
        try:
            analytics_payload = message.payload
            analytics_data = AnalyticsData(**analytics_payload)

            # Store in local cache
            cache_key = f"{analytics_data.data_type}:{analytics_data.origin_swarm}:{analytics_data.timestamp}"
            self.analytics_cache[cache_key] = analytics_data

            # Notify callback
            if self.on_analytics_received:
                try:
                    self.on_analytics_received(analytics_data)
                except Exception as e:
                    logger.error(f"Error in analytics received callback: {e}")

            logger.debug(f"Received analytics data {cache_key} from {message.sender_swarm_id}")

        except Exception as e:
            logger.error(f"Error processing analytics share: {e}")

    # Resource Management Methods

    async def request_resources(self, resource_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request resources from connected swarms.

        Args:
            resource_requirements: Description of needed resources

        Returns:
            Available resources from connected swarms
        """
        responses = await self.connection_manager.broadcast_message(
            "resource_request",
            {"requirements": resource_requirements},
            requires_response=True
        )

        available_resources = {}
        for swarm_id, response in responses.items():
            if response and response.payload.get("available_resources"):
                available_resources[swarm_id] = response.payload["available_resources"]

        return available_resources

    def _handle_resource_request(self, message: FederationMessage):
        """Handle incoming resource request."""
        # Would check local resources and respond
        pass

    # Federation-wide Coordination

    def get_federation_metrics(self) -> Dict[str, Any]:
        """Get comprehensive federation metrics."""
        connected_swarms = self.connection_manager.get_connected_swarms()

        return {
            "federation_health": len(connected_swarms) > 0,
            "total_connected_swarms": len(connected_swarms),
            "shared_tasks_count": len(self.shared_tasks),
            "memory_cache_size": len(self.memory_cache),
            "analytics_cache_size": len(self.analytics_cache),
            "connected_swarm_ids": connected_swarms,
            "federation_capabilities": ["task_sharing", "memory_sync", "analytics_sharing", "resource_sharing"]
        }

    async def optimize_federation(self) -> Dict[str, List[Dict[str, Any]]]:
        """Perform federation-wide optimization."""
        # This would implement load balancing, resource optimization, etc.
        return {
            "load_balancing_actions": [],
            "resource_sharing_actions": [],
            "communication_optimization": [],
            "task_redistribution": []
        }

    def set_memory_manager(self, memory_manager: Any):
        """Set the memory manager for integration."""
        self.memory_manager = memory_manager

    def set_analytics_manager(self, analytics_manager: Any):
        """Set the analytics manager for integration."""
        self.analytics_manager = analytics_manager

    def set_task_manager(self, task_manager: Any):
        """Set the task manager for integration."""
        self.task_manager = task_manager


class SwarmManager:
    """Manages multiple swarms in the federation with federation capabilities"""

    def __init__(self, federation_manager: FederationManager):
        self.federation_manager = federation_manager
        self.swarms: Dict[str, Any] = {}
        self.swarm_stats: Dict[str, Dict[str, Any]] = {}

    def get_swarm(self, swarm_id: str) -> Optional[Any]:
        """Get a swarm by ID"""
        return self.swarms.get(swarm_id)

    def get_swarm_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all swarms including federation data"""
        stats = self.swarm_stats.copy()

        # Add federation metrics
        federation_metrics = self.federation_manager.get_federation_metrics()
        stats["federation"] = federation_metrics

        return stats


class FederationOrchestrator:
    """
    High-level orchestrator that manages the complete federation lifecycle,
    integrating discovery, connections, and cross-swarm coordination.
    """

    def __init__(self,
                 local_swarm_id: str,
                 local_node_name: str = "local-node",
                 federation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the federation orchestrator.

        Args:
            local_swarm_id: Unique identifier for this swarm
            local_node_name: Human-readable name for this node
            federation_config: Configuration for federation behavior
        """
        self.local_swarm_id = local_swarm_id
        self.local_node_name = local_node_name
        self.config = federation_config or self._get_default_config()

        # Core components
        self.discovery_layer: Optional[DiscoveryLayer] = None
        self.federation_manager: Optional[FederationManager] = None
        self.swarm_manager: Optional[SwarmManager] = None

        # Federation state
        self.is_running = False
        self.start_time: Optional[float] = None

        # Integration managers
        self.memory_manager: Optional[Any] = None
        self.analytics_manager: Optional[Any] = None
        self.task_manager: Optional[Any] = None

        logger.info(f"Federation orchestrator initialized for {local_swarm_id}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default federation configuration."""
        return {
            "discovery": {
                "enabled": True,
                "broadcast_port": 9999,
                "api_port": 8000,
                "broadcast_interval": 30.0,
                "discovery_timeout": 300.0
            },
            "connection": {
                "auth_token": "federation-token-123",  # Should be configurable
                "reconnect_interval": 30.0,
                "heartbeat_interval": 60.0
            },
            "sharing": {
                "enable_task_sharing": True,
                "enable_memory_sync": True,
                "enable_analytics_sharing": True,
                "auto_discovery_connections": True
            },
            "monitoring": {
                "metrics_interval": 60.0,
                "health_check_interval": 30.0
            }
        }

    def configure_discovery(self,
                           broadcast_port: int = 9999,
                           api_port: int = 8000,
                           broadcast_interval: float = 30.0) -> 'FederationOrchestrator':
        """Configure the discovery layer."""
        self.config["discovery"].update({
            "broadcast_port": broadcast_port,
            "api_port": api_port,
            "broadcast_interval": broadcast_interval
        })
        return self

    def configure_connections(self,
                             auth_token: str = None,
                             reconnect_interval: float = 30.0) -> 'FederationOrchestrator':
        """Configure connection parameters."""
        updates = {"reconnect_interval": reconnect_interval}
        if auth_token:
            updates["auth_token"] = auth_token
        self.config["connection"].update(updates)
        return self

    def set_memory_manager(self, memory_manager: Any) -> 'FederationOrchestrator':
        """Set the memory manager for federation integration."""
        self.memory_manager = memory_manager
        return self

    def set_analytics_manager(self, analytics_manager: Any) -> 'FederationOrchestrator':
        """Set the analytics manager for federation integration."""
        self.analytics_manager = analytics_manager
        return self

    def set_task_manager(self, task_manager: Any) -> 'FederationOrchestrator':
        """Set the task manager for federation integration."""
        self.task_manager = task_manager
        return self

    async def initialize(self) -> 'FederationOrchestrator':
        """Initialize all federation components."""
        logger.info("Initializing federation components...")

        # Initialize discovery layer
        if self.config["discovery"]["enabled"]:
            self.discovery_layer = DiscoveryLayer(
                swarm_id=self.local_swarm_id,
                node_name=self.local_node_name,
                broadcast_port=self.config["discovery"]["broadcast_port"],
                api_port=self.config["discovery"]["api_port"],
                broadcast_interval=self.config["discovery"]["broadcast_interval"],
                discovery_timeout=self.config["discovery"]["discovery_timeout"]
            )

        # Initialize federation manager
        self.federation_manager = FederationManager(
            local_swarm_id=self.local_swarm_id,
            auth_token=self.config["connection"]["auth_token"],
            discovery_layer=self.discovery_layer
        )

        # Set up integrations
        if self.memory_manager:
            self.federation_manager.set_memory_manager(self.memory_manager)
        if self.analytics_manager:
            self.federation_manager.set_analytics_manager(self.analytics_manager)
        if self.task_manager:
            self.federation_manager.set_task_manager(self.task_manager)

        # Initialize swarm manager
        self.swarm_manager = SwarmManager(self.federation_manager)

        # Set up discovery callbacks for auto-connection
        if self.discovery_layer and self.config["sharing"]["auto_discovery_connections"]:
            self.discovery_layer.on_swarm_discovered = self._on_swarm_discovered
            self.discovery_layer.on_swarm_lost = self._on_swarm_lost

        logger.info("Federation components initialized")
        return self

    async def start(self) -> 'FederationOrchestrator':
        """Start the federation."""
        if self.is_running:
            logger.warning("Federation already running")
            return self

        logger.info("Starting federation...")

        if not self.federation_manager:
            await self.initialize()

        # Start discovery
        if self.discovery_layer:
            self.discovery_layer.start()

        # Start federation connections
        await self.federation_manager.start_federation()

        # Start monitoring
        asyncio.create_task(self._monitoring_loop())

        self.is_running = True
        self.start_time = time.time()

        logger.info(f"Federation started for swarm {self.local_swarm_id}")
        return self

    async def stop(self) -> 'FederationOrchestrator':
        """Stop the federation."""
        if not self.is_running:
            logger.warning("Federation not running")
            return self

        logger.info("Stopping federation...")

        # Stop federation connections
        if self.federation_manager:
            await self.federation_manager.stop_federation()

        # Stop discovery
        if self.discovery_layer:
            self.discovery_layer.stop()

        self.is_running = False
        logger.info("Federation stopped")
        return self

    def _on_swarm_discovered(self, swarm_metadata: SwarmMetadata):
        """Handle swarm discovery."""
        logger.info(f"Swarm discovered: {swarm_metadata.swarm_id}")

        if self.config["sharing"]["auto_discovery_connections"]:
            # Auto-connect to discovered swarm
            asyncio.create_task(self._connect_to_discovered_swarm(swarm_metadata))

    def _on_swarm_lost(self, swarm_metadata: SwarmMetadata):
        """Handle swarm loss."""
        logger.info(f"Swarm lost: {swarm_metadata.swarm_id}")

        # The connection manager will handle disconnection automatically
        # Could trigger task redistribution or other recovery actions

    async def _connect_to_discovered_swarm(self, swarm_metadata: SwarmMetadata):
        """Connect to a newly discovered swarm."""
        if not self.federation_manager:
            return

        try:
            await self.federation_manager.connection_manager.connect_to_swarm(swarm_metadata)
            logger.info(f"Auto-connected to discovered swarm: {swarm_metadata.swarm_id}")
        except Exception as e:
            logger.error(f"Failed to auto-connect to {swarm_metadata.swarm_id}: {e}")

    async def _monitoring_loop(self):
        """Periodic monitoring and health checks."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config["monitoring"]["metrics_interval"])

                # Collect and log federation metrics
                if self.federation_manager:
                    metrics = self.federation_manager.get_federation_metrics()
                    logger.info(f"Federation metrics: {metrics}")

                # Perform health checks
                await self._perform_health_checks()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _perform_health_checks(self):
        """Perform federation health checks."""
        # Check discovery layer
        if self.discovery_layer:
            discovery_stats = self.discovery_layer.get_discovery_stats()
            if not discovery_stats["is_running"]:
                logger.warning("Discovery layer is not running")

        # Check connections
        if self.federation_manager:
            connected_swarms = self.federation_manager.connection_manager.get_connected_swarms()
            if len(connected_swarms) == 0:
                logger.info("No active federation connections")

    # High-level federation operations

    async def share_task_federation_wide(self, task: SharedTask) -> bool:
        """Share a task across the entire federation."""
        if not self.federation_manager:
            return False

        return await self.federation_manager.share_task(task)

    async def request_federation_resources(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Request resources from federation."""
        if not self.federation_manager:
            return {}

        return await self.federation_manager.request_resources(requirements)

    async def synchronize_memory_federation(self, memory_data: MemorySync) -> bool:
        """Synchronize memory across federation."""
        if not self.federation_manager:
            return False

        await self.federation_manager.share_memory(memory_data)
        return True

    async def broadcast_analytics_federation(self, analytics: AnalyticsData) -> bool:
        """Broadcast analytics data to federation."""
        if not self.federation_manager:
            return False

        await self.federation_manager.share_analytics(analytics)
        return True

    def get_federation_status(self) -> Dict[str, Any]:
        """Get comprehensive federation status."""
        status = {
            "is_running": self.is_running,
            "local_swarm_id": self.local_swarm_id,
            "local_node_name": self.local_node_name,
            "start_time": self.start_time,
            "uptime": time.time() - (self.start_time or time.time()) if self.start_time else 0
        }

        if self.discovery_layer:
            status["discovery"] = self.discovery_layer.get_discovery_stats()

        if self.federation_manager:
            status["federation"] = self.federation_manager.get_federation_metrics()

        return status

    async def optimize_federation_resources(self) -> Dict[str, Any]:
        """Perform federation-wide resource optimization."""
        if not self.federation_manager:
            return {"error": "Federation manager not initialized"}

        return await self.federation_manager.optimize_federation()


# Global instances (to be initialized by application)
federation_manager: Optional[FederationManager] = None
swarm_manager: Optional[SwarmManager] = None
federation_orchestrator: Optional[FederationOrchestrator] = None


def initialize_federation(local_swarm_id: str,
                         auth_token: str,
                         discovery_layer: Optional[DiscoveryLayer] = None) -> FederationManager:
    """
    Initialize the global federation manager.

    Args:
        local_swarm_id: ID of the local swarm
        auth_token: Authentication token for federation
        discovery_layer: Discovery layer instance

    Returns:
        Configured FederationManager instance
    """
    global federation_manager, swarm_manager

    federation_manager = FederationManager(local_swarm_id, auth_token, discovery_layer)
    swarm_manager = SwarmManager(federation_manager)

    return federation_manager


async def initialize_federation_orchestrator(local_swarm_id: str,
                                           local_node_name: str = "local-node",
                                           config: Optional[Dict[str, Any]] = None) -> FederationOrchestrator:
    """
    Initialize the complete federation orchestrator.

    Args:
        local_swarm_id: Unique identifier for this swarm
        local_node_name: Human-readable name for this node
        config: Federation configuration

    Returns:
        Configured FederationOrchestrator instance
    """
    global federation_orchestrator

    federation_orchestrator = FederationOrchestrator(
        local_swarm_id=local_swarm_id,
        local_node_name=local_node_name,
        federation_config=config
    )

    await federation_orchestrator.initialize()
    return federation_orchestrator


def get_federation_status() -> Dict[str, Any]:
    """Get the current federation status."""
    if federation_orchestrator:
        return federation_orchestrator.get_federation_status()
    elif federation_manager:
        return {
            "federation_manager_active": True,
            "metrics": federation_manager.get_federation_metrics()
        }
    else:
        return {"status": "no_federation_active"}