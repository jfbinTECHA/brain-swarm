from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from .base import logger, metrics
import time
import json
import uuid
import threading
import socket
import requests
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import random
from collections import defaultdict, deque
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import psutil
import platform

class NodeRole(Enum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    GATEWAY = "gateway"
    STORAGE = "storage"
    MONITOR = "monitor"

class NodeStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    STARTING = "starting"
    STOPPING = "stopping"

class DeploymentStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    GEOGRAPHIC = "geographic"
    SPECIALIZED = "specialized"
    REDUNDANT = "redundant"

class CommunicationProtocol(Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    MESSAGE_QUEUE = "message_queue"

@dataclass
class SwarmNode:
    """Represents a node in the multi-node swarm deployment"""
    node_id: str
    hostname: str
    ip_address: str
    role: NodeRole
    status: NodeStatus = NodeStatus.STARTING
    capabilities: Set[str] = field(default_factory=set)
    resources: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_response_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_latency: float = 0.0

@dataclass
class TaskDistribution:
    """Represents task distribution across nodes"""
    task_id: str
    assigned_node: str
    distribution_strategy: DeploymentStrategy
    assigned_at: float
    estimated_completion: Optional[float] = None
    actual_completion: Optional[float] = None
    status: str = "assigned"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DataSynchronization:
    """Represents data synchronization between nodes"""
    sync_id: str
    source_node: str
    target_nodes: List[str]
    data_type: str
    sync_status: str = "pending"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    data_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LoadBalancingMetrics:
    """Load balancing metrics for the swarm"""
    total_nodes: int = 0
    active_nodes: int = 0
    total_tasks: int = 0
    tasks_per_node: Dict[str, int] = field(default_factory=dict)
    node_utilization: Dict[str, float] = field(default_factory=dict)
    load_distribution_score: float = 0.0
    last_updated: float = field(default_factory=time.time)

class MultiNodeCoordinator:
    """Central coordinator for multi-node swarm deployment"""

    def __init__(self, coordinator_id: str = None, listen_port: int = 8080):
        self.coordinator_id = coordinator_id or f"coordinator_{uuid.uuid4().hex[:8]}"
        self.listen_port = listen_port

        # Node management
        self.nodes: Dict[str, SwarmNode] = {}
        self.node_lock = threading.Lock()

        # Task distribution
        self.task_distributions: Dict[str, TaskDistribution] = {}
        self.distribution_lock = threading.Lock()

        # Data synchronization
        self.data_syncs: Dict[str, DataSynchronization] = {}
        self.sync_lock = threading.Lock()

        # Load balancing
        self.load_metrics = LoadBalancingMetrics()
        self.load_lock = threading.Lock()

        # Communication
        self.communication_protocol = CommunicationProtocol.HTTP
        self.message_queue: deque = deque(maxlen=10000)

        # Configuration
        self.heartbeat_interval = 30  # seconds
        self.node_timeout = 90  # seconds
        self.max_tasks_per_node = 10
        self.load_balance_interval = 60  # seconds

        # Deployment strategies
        self.deployment_strategies = {
            DeploymentStrategy.ROUND_ROBIN: self._round_robin_distribution,
            DeploymentStrategy.LEAST_LOADED: self._least_loaded_distribution,
            DeploymentStrategy.GEOGRAPHIC: self._geographic_distribution,
            DeploymentStrategy.SPECIALIZED: self._specialized_distribution,
            DeploymentStrategy.REDUNDANT: self._redundant_distribution
        }

        # Background threads
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.load_balance_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False

        # HTTP server for node communication
        self.http_server = None

    def start(self):
        """Start the multi-node coordinator"""
        logger.log("INFO", "MultiNodeCoordinator", f"Starting multi-node coordinator {self.coordinator_id}")

        self.running = True

        # Start background threads
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
        self.load_balance_thread = threading.Thread(target=self._load_balancer, daemon=True)
        self.monitoring_thread = threading.Thread(target=self._node_monitor, daemon=True)

        self.heartbeat_thread.start()
        self.load_balance_thread.start()
        self.monitoring_thread.start()

        # Start HTTP server for node communication
        self._start_http_server()

        logger.log("INFO", "MultiNodeCoordinator", "Multi-node coordinator started successfully")

    def stop(self):
        """Stop the multi-node coordinator"""
        logger.log("INFO", "MultiNodeCoordinator", f"Stopping multi-node coordinator {self.coordinator_id}")

        self.running = False

        # Stop HTTP server
        if self.http_server:
            self.http_server.shutdown()

        # Wait for threads to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        if self.load_balance_thread and self.load_balance_thread.is_alive():
            self.load_balance_thread.join(timeout=5)
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        logger.log("INFO", "MultiNodeCoordinator", "Multi-node coordinator stopped")

    def register_node(self, node_info: Dict[str, Any]) -> str:
        """Register a new node with the coordinator"""

        node_id = node_info.get('node_id') or f"node_{uuid.uuid4().hex[:8]}"

        with self.node_lock:
            if node_id in self.nodes:
                # Update existing node
                node = self.nodes[node_id]
                node.status = NodeStatus.ONLINE
                node.last_heartbeat = time.time()
                node.resources = node_info.get('resources', node.resources)
                node.capabilities = set(node_info.get('capabilities', node.capabilities))
                node.metadata.update(node_info.get('metadata', {}))
            else:
                # Create new node
                node = SwarmNode(
                    node_id=node_id,
                    hostname=node_info.get('hostname', 'unknown'),
                    ip_address=node_info.get('ip_address', 'unknown'),
                    role=NodeRole(node_info.get('role', 'worker')),
                    capabilities=set(node_info.get('capabilities', [])),
                    resources=node_info.get('resources', {}),
                    metadata=node_info.get('metadata', {})
                )
                self.nodes[node_id] = node

        logger.log("INFO", "MultiNodeCoordinator", f"Registered node {node_id} ({node.role.value})")
        return node_id

    def unregister_node(self, node_id: str):
        """Unregister a node"""

        with self.node_lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.status = NodeStatus.OFFLINE

                # Redistribute tasks from this node
                self._redistribute_node_tasks(node_id)

                logger.log("INFO", "MultiNodeCoordinator", f"Unregistered node {node_id}")

    def distribute_task(self, task_context: Dict[str, Any], strategy: DeploymentStrategy = None) -> Optional[str]:
        """Distribute a task to an appropriate node"""

        if strategy is None:
            strategy = self._select_distribution_strategy(task_context)

        distribution_func = self.deployment_strategies.get(strategy)
        if not distribution_func:
            logger.log("ERROR", "MultiNodeCoordinator", f"Unknown distribution strategy: {strategy}")
            return None

        target_node = distribution_func(task_context)
        if not target_node:
            logger.log("WARNING", "MultiNodeCoordinator", f"No suitable node found for task using {strategy.value} strategy")
            return None

        task_id = task_context.get('task_id', f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}")

        # Create task distribution record
        distribution = TaskDistribution(
            task_id=task_id,
            assigned_node=target_node,
            distribution_strategy=strategy,
            assigned_at=time.time(),
            metadata=task_context
        )

        with self.distribution_lock:
            self.task_distributions[task_id] = distribution

        # Update node load
        with self.node_lock:
            if target_node in self.nodes:
                self.nodes[target_node].active_tasks += 1

        # Send task to node
        self._send_task_to_node(target_node, task_context)

        logger.log("INFO", "MultiNodeCoordinator", f"Distributed task {task_id} to node {target_node} using {strategy.value}")
        return target_node

    def _select_distribution_strategy(self, task_context: Dict[str, Any]) -> DeploymentStrategy:
        """Select the appropriate distribution strategy based on task context"""

        task_type = task_context.get('task_type', 'general')
        urgency = task_context.get('urgency', 'normal')
        required_capabilities = set(task_context.get('required_capabilities', []))

        # High urgency tasks use least loaded strategy
        if urgency in ['critical', 'high']:
            return DeploymentStrategy.LEAST_LOADED

        # Tasks requiring specific capabilities use specialized distribution
        if required_capabilities:
            return DeploymentStrategy.SPECIALIZED

        # Geographic distribution for location-specific tasks
        if task_context.get('location_constraint'):
            return DeploymentStrategy.GEOGRAPHIC

        # Redundant distribution for critical tasks
        if task_context.get('redundancy_required', False):
            return DeploymentStrategy.REDUNDANT

        # Default to round-robin for general load balancing
        return DeploymentStrategy.ROUND_ROBIN

    def _round_robin_distribution(self, task_context: Dict[str, Any]) -> Optional[str]:
        """Round-robin task distribution"""

        with self.node_lock:
            available_nodes = [node_id for node_id, node in self.nodes.items()
                             if node.status == NodeStatus.ONLINE and
                             node.role in [NodeRole.WORKER, NodeRole.COORDINATOR] and
                             node.active_tasks < self.max_tasks_per_node]

        if not available_nodes:
            return None

        # Simple round-robin using task count as index
        task_count = len(self.task_distributions)
        selected_index = task_count % len(available_nodes)
        return available_nodes[selected_index]

    def _least_loaded_distribution(self, task_context: Dict[str, Any]) -> Optional[str]:
        """Least loaded node distribution"""

        with self.node_lock:
            available_nodes = [(node_id, node) for node_id, node in self.nodes.items()
                             if node.status == NodeStatus.ONLINE and
                             node.role in [NodeRole.WORKER, NodeRole.COORDINATOR]]

        if not available_nodes:
            return None

        # Sort by active tasks (ascending)
        available_nodes.sort(key=lambda x: x[1].active_tasks)
        return available_nodes[0][0]

    def _geographic_distribution(self, task_context: Dict[str, Any]) -> Optional[str]:
        """Geographic distribution based on location constraints"""

        location_constraint = task_context.get('location_constraint')
        if not location_constraint:
            return self._round_robin_distribution(task_context)

        with self.node_lock:
            available_nodes = [node_id for node_id, node in self.nodes.items()
                             if node.status == NodeStatus.ONLINE and
                             node.metadata.get('location') == location_constraint and
                             node.active_tasks < self.max_tasks_per_node]

        return available_nodes[0] if available_nodes else None

    def _specialized_distribution(self, task_context: Dict[str, Any]) -> Optional[str]:
        """Specialized distribution based on required capabilities"""

        required_capabilities = set(task_context.get('required_capabilities', []))

        with self.node_lock:
            available_nodes = []
            for node_id, node in self.nodes.items():
                if (node.status == NodeStatus.ONLINE and
                    node.role in [NodeRole.WORKER, NodeRole.COORDINATOR] and
                    node.active_tasks < self.max_tasks_per_node and
                    required_capabilities.issubset(node.capabilities)):
                    available_nodes.append((node_id, node))

        if not available_nodes:
            return None

        # Prefer least loaded among capable nodes
        available_nodes.sort(key=lambda x: x[1].active_tasks)
        return available_nodes[0][0]

    def _redundant_distribution(self, task_context: Dict[str, Any]) -> Optional[str]:
        """Redundant distribution for critical tasks"""

        # For redundant tasks, we might want to distribute to multiple nodes
        # For now, just use least loaded but mark for redundancy
        target_node = self._least_loaded_distribution(task_context)

        if target_node:
            # Mark task for potential replication
            task_context['redundancy_enabled'] = True

        return target_node

    def synchronize_data(self, source_node: str, target_nodes: List[str], data_type: str, data: Any) -> str:
        """Synchronize data between nodes"""

        sync_id = f"sync_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        sync = DataSynchronization(
            sync_id=sync_id,
            source_node=source_node,
            target_nodes=target_nodes,
            data_type=data_type,
            data_size=len(str(data).encode('utf-8')) if data else 0,
            metadata={'data_hash': hashlib.md5(str(data).encode()).hexdigest() if data else ''}
        )

        with self.sync_lock:
            self.data_syncs[sync_id] = sync

        # Start synchronization process
        threading.Thread(target=self._perform_data_sync, args=(sync, data), daemon=True).start()

        logger.log("INFO", "MultiNodeCoordinator", f"Started data synchronization {sync_id} from {source_node}")
        return sync_id

    def _perform_data_sync(self, sync: DataSynchronization, data: Any):
        """Perform the actual data synchronization"""

        sync.sync_status = "in_progress"

        success_count = 0
        for target_node in sync.target_nodes:
            try:
                self._send_data_to_node(target_node, sync.data_type, data)
                success_count += 1
            except Exception as e:
                logger.log("ERROR", "MultiNodeCoordinator", f"Failed to sync data to node {target_node}: {str(e)}")

        sync.sync_status = "completed" if success_count == len(sync.target_nodes) else "partial"
        sync.completed_at = time.time()

        logger.log("INFO", "MultiNodeCoordinator", f"Data synchronization {sync.sync_id} completed: {success_count}/{len(sync.target_nodes)} successful")

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status"""

        with self.node_lock:
            node_status = {
                node_id: {
                    'status': node.status.value,
                    'role': node.role.value,
                    'active_tasks': node.active_tasks,
                    'cpu_usage': node.cpu_usage,
                    'memory_usage': node.memory_usage,
                    'last_heartbeat': node.last_heartbeat
                }
                for node_id, node in self.nodes.items()
            }

        with self.load_lock:
            load_status = {
                'total_nodes': self.load_metrics.total_nodes,
                'active_nodes': self.load_metrics.active_nodes,
                'total_tasks': self.load_metrics.total_tasks,
                'load_distribution_score': self.load_metrics.load_distribution_score,
                'node_utilization': self.load_metrics.node_utilization.copy()
            }

        return {
            'coordinator_id': self.coordinator_id,
            'nodes': node_status,
            'load_metrics': load_status,
            'active_distributions': len([d for d in self.task_distributions.values() if d.status == 'assigned']),
            'completed_distributions': len([d for d in self.task_distributions.values() if d.status == 'completed']),
            'active_syncs': len([s for s in self.data_syncs.values() if s.sync_status in ['pending', 'in_progress']]),
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }

    def _heartbeat_monitor(self):
        """Monitor node heartbeats and detect offline nodes"""

        while self.running:
            current_time = time.time()

            with self.node_lock:
                offline_nodes = []
                for node_id, node in self.nodes.items():
                    if current_time - node.last_heartbeat > self.node_timeout:
                        if node.status != NodeStatus.OFFLINE:
                            node.status = NodeStatus.OFFLINE
                            offline_nodes.append(node_id)
                            logger.log("WARNING", "MultiNodeCoordinator", f"Node {node_id} marked as offline (heartbeat timeout)")

                # Redistribute tasks from offline nodes
                for node_id in offline_nodes:
                    self._redistribute_node_tasks(node_id)

            time.sleep(self.heartbeat_interval)

    def _load_balancer(self):
        """Perform load balancing across nodes"""

        while self.running:
            try:
                self._update_load_metrics()
                self._perform_load_balancing()
            except Exception as e:
                logger.log("ERROR", "MultiNodeCoordinator", f"Load balancing error: {str(e)}")

            time.sleep(self.load_balance_interval)

    def _update_load_metrics(self):
        """Update load balancing metrics"""

        with self.node_lock:
            active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ONLINE]
            total_tasks = sum(node.active_tasks for node in active_nodes)

            with self.load_lock:
                self.load_metrics.total_nodes = len(self.nodes)
                self.load_metrics.active_nodes = len(active_nodes)
                self.load_metrics.total_tasks = total_tasks

                # Update per-node metrics
                for node in active_nodes:
                    self.load_metrics.tasks_per_node[node.node_id] = node.active_tasks
                    # Calculate utilization as percentage of max capacity
                    utilization = (node.active_tasks / self.max_tasks_per_node) * 100
                    self.load_metrics.node_utilization[node.node_id] = utilization

                # Calculate load distribution score (lower is better)
                if active_nodes:
                    avg_tasks = total_tasks / len(active_nodes)
                    variance = sum((node.active_tasks - avg_tasks) ** 2 for node in active_nodes) / len(active_nodes)
                    self.load_metrics.load_distribution_score = variance ** 0.5  # Standard deviation

                self.load_metrics.last_updated = time.time()

    def _perform_load_balancing(self):
        """Perform actual load balancing by redistributing tasks"""

        with self.load_lock:
            if self.load_metrics.load_distribution_score < 2.0:  # Acceptable distribution
                return

            # Find overloaded and underloaded nodes
            overloaded = []
            underloaded = []

            for node_id, utilization in self.load_metrics.node_utilization.items():
                if utilization > 80:  # Over 80% capacity
                    overloaded.append(node_id)
                elif utilization < 30:  # Under 30% capacity
                    underloaded.append(node_id)

            if not overloaded or not underloaded:
                return

            # Redistribute tasks from overloaded to underloaded nodes
            tasks_redistributed = 0
            for overloaded_node in overloaded:
                # Find tasks that can be moved
                movable_tasks = [task_id for task_id, dist in self.task_distributions.items()
                               if dist.assigned_node == overloaded_node and
                               dist.status == 'assigned' and
                               not dist.metadata.get('pinned', False)]  # Don't move pinned tasks

                for task_id in movable_tasks[:2]:  # Move max 2 tasks per overloaded node
                    target_node = random.choice(underloaded)
                    self._redistribute_task(task_id, target_node)
                    tasks_redistributed += 1

            if tasks_redistributed > 0:
                logger.log("INFO", "MultiNodeCoordinator", f"Load balanced: redistributed {tasks_redistributed} tasks")

    def _redistribute_node_tasks(self, node_id: str):
        """Redistribute all tasks from a node (e.g., when it goes offline)"""

        tasks_to_redistribute = [task_id for task_id, dist in self.task_distributions.items()
                               if dist.assigned_node == node_id and dist.status == 'assigned']

        redistributed = 0
        for task_id in tasks_to_redistribute:
            # Try to redistribute using least loaded strategy
            new_node = self._least_loaded_distribution({})
            if new_node:
                self._redistribute_task(task_id, new_node)
                redistributed += 1

        if redistributed > 0:
            logger.log("INFO", "MultiNodeCoordinator", f"Redistributed {redistributed} tasks from offline node {node_id}")

    def _redistribute_task(self, task_id: str, new_node: str):
        """Redistribute a specific task to a new node"""

        with self.distribution_lock:
            if task_id not in self.task_distributions:
                return

            distribution = self.task_distributions[task_id]
            old_node = distribution.assigned_node

            # Update distribution
            distribution.assigned_node = new_node
            distribution.metadata['redistributed_from'] = old_node
            distribution.metadata['redistributed_at'] = time.time()

            # Update node loads
            with self.node_lock:
                if old_node in self.nodes:
                    self.nodes[old_node].active_tasks = max(0, self.nodes[old_node].active_tasks - 1)
                if new_node in self.nodes:
                    self.nodes[new_node].active_tasks += 1

            # Send task to new node
            self._send_task_to_node(new_node, distribution.metadata)

            logger.log("INFO", "MultiNodeCoordinator", f"Redistributed task {task_id} from {old_node} to {new_node}")

    def _node_monitor(self):
        """Monitor node health and performance"""

        while self.running:
            try:
                self._collect_node_metrics()
            except Exception as e:
                logger.log("ERROR", "MultiNodeCoordinator", f"Node monitoring error: {str(e)}")

            time.sleep(60)  # Monitor every minute

    def _collect_node_metrics(self):
        """Collect performance metrics from all nodes"""

        with self.node_lock:
            for node_id, node in self.nodes.items():
                if node.status == NodeStatus.ONLINE:
                    try:
                        # In a real implementation, this would query the node
                        # For now, we'll simulate metric collection
                        node.cpu_usage = random.uniform(10, 90)
                        node.memory_usage = random.uniform(20, 95)
                        node.network_latency = random.uniform(1, 50)
                    except Exception as e:
                        logger.log("ERROR", "MultiNodeCoordinator", f"Failed to collect metrics from node {node_id}: {str(e)}")

    def _send_task_to_node(self, node_id: str, task_context: Dict[str, Any]):
        """Send a task to a specific node"""

        # In a real implementation, this would use the appropriate communication protocol
        # For now, we'll simulate the task assignment
        logger.log("DEBUG", "MultiNodeCoordinator", f"Simulating task send to node {node_id}")

    def _send_data_to_node(self, node_id: str, data_type: str, data: Any):
        """Send data to a specific node for synchronization"""

        # In a real implementation, this would use the appropriate communication protocol
        logger.log("DEBUG", "MultiNodeCoordinator", f"Simulating data sync to node {node_id}")

    def _start_http_server(self):
        """Start HTTP server for node communication"""

        # In a real implementation, this would start an HTTP server
        # For now, we'll just log that it would start
        logger.log("INFO", "MultiNodeCoordinator", f"HTTP server would start on port {self.listen_port}")

# Global multi-node coordinator instance
multi_node_coordinator = MultiNodeCoordinator()

# Integration functions
def start_multi_node_coordinator(port: int = 8080) -> MultiNodeCoordinator:
    """Start the multi-node coordinator"""
    coordinator = MultiNodeCoordinator(listen_port=port)
    coordinator.start()
    return coordinator

def register_swarm_node(node_info: Dict[str, Any]) -> str:
    """Register a node with the multi-node coordinator"""
    return multi_node_coordinator.register_node(node_info)

def distribute_task_to_nodes(task_context: Dict[str, Any], strategy: DeploymentStrategy = None) -> Optional[str]:
    """Distribute a task across the multi-node swarm"""
    return multi_node_coordinator.distribute_task(task_context, strategy)

def synchronize_swarm_data(source_node: str, target_nodes: List[str], data_type: str, data: Any) -> str:
    """Synchronize data across swarm nodes"""
    return multi_node_coordinator.synchronize_data(source_node, target_nodes, data_type, data)

def get_swarm_deployment_status() -> Dict[str, Any]:
    """Get comprehensive multi-node swarm status"""
    return multi_node_coordinator.get_swarm_status()

def stop_multi_node_coordinator():
    """Stop the multi-node coordinator"""
    multi_node_coordinator.stop()