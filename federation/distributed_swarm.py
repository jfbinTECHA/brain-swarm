from typing import Dict, List, Any, Optional, Tuple, Set
from core.base import logger, metrics
import time
import json
import threading
import socket
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class SwarmNode:
    """Represents a node in the distributed swarm"""
    node_id: str
    host: str
    port: int
    status: str = "unknown"  # unknown, online, offline, degraded
    last_heartbeat: float = 0
    capabilities: List[str] = None
    agent_count: int = 0
    load_factor: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    network_latency: float = 0.0
    region: str = "default"
    zone: str = "default"
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.tags is None:
            self.tags = {}

    def is_healthy(self) -> bool:
        """Check if node is healthy based on various metrics"""
        current_time = time.time()
        time_since_heartbeat = current_time - self.last_heartbeat

        # Node is unhealthy if:
        # - No heartbeat for more than 30 seconds
        # - Load factor > 95%
        # - Memory usage > 90%
        # - CPU usage > 95%
        return (
            time_since_heartbeat < 30 and
            self.load_factor < 0.95 and
            self.memory_usage < 0.9 and
            self.cpu_usage < 0.95 and
            self.status == "online"
        )

    def get_health_score(self) -> float:
        """Calculate overall health score (0-1, higher is better)"""
        if not self.is_healthy():
            return 0.0

        # Weighted health score based on various metrics
        load_score = 1.0 - self.load_factor
        memory_score = 1.0 - self.memory_usage
        cpu_score = 1.0 - self.cpu_usage
        latency_score = max(0, 1.0 - (self.network_latency / 1000))  # Penalize >1s latency

        # Weighted average
        return (load_score * 0.3 + memory_score * 0.3 + cpu_score * 0.3 + latency_score * 0.1)

@dataclass
class DistributedTask:
    """Represents a task in the distributed swarm"""
    task_id: str
    description: str
    assigned_node: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    priority: int = 1
    requirements: Dict[str, Any] = None
    result: Any = None
    created_at: float = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = {}
        if self.tags is None:
            self.tags = {}
        if self.created_at == 0:
            self.created_at = time.time()

    def execution_time(self) -> Optional[float]:
        """Get task execution time if completed"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    def total_time(self) -> float:
        """Get total time since task creation"""
        return time.time() - self.created_at

@dataclass
class ClusterConfig:
    """Configuration for a swarm cluster"""
    cluster_id: str
    name: str
    nodes: List[str] = None  # Node IDs in this cluster
    primary_node: Optional[str] = None
    backup_nodes: List[str] = None
    load_balancing_strategy: str = "round_robin"  # round_robin, least_loaded, capability_based
    failover_enabled: bool = True
    auto_scaling_enabled: bool = False
    min_nodes: int = 1
    max_nodes: int = 10
    region: str = "default"
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.backup_nodes is None:
            self.backup_nodes = []
        if self.tags is None:
            self.tags = {}

class DistributedCoordinator:
    """Central coordinator for multi-node swarm deployment"""

    def __init__(self, coordinator_id: str = None):
        self.coordinator_id = coordinator_id or f"coordinator_{uuid.uuid4().hex[:8]}"
        self.nodes: Dict[str, SwarmNode] = {}
        self.clusters: Dict[str, ClusterConfig] = {}
        self.tasks: Dict[str, DistributedTask] = {}
        self.node_tasks: Dict[str, Set[str]] = defaultdict(set)  # node_id -> set of task_ids

        # Communication
        self.message_queue: List[Dict[str, Any]] = []
        self.heartbeat_interval = 10  # seconds
        self.task_sync_interval = 30  # seconds

        # Load balancing
        self.load_balancer = DistributedLoadBalancer(self)

        # Health monitoring
        self.health_monitor = SwarmHealthMonitor(self)

        # Auto-scaling
        self.auto_scaler = AutoScaler(self)

        # Communication threads
        self.running = False
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.task_sync_thread: Optional[threading.Thread] = None

        # Initialize default cluster
        self.create_cluster("default", "Default Cluster")

    def start(self):
        """Start the distributed coordinator"""
        self.running = True
        logger.log("INFO", "DistributedCoordinator", f"Starting distributed coordinator {self.coordinator_id}")

        # Start background threads
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.task_sync_thread = threading.Thread(target=self._task_sync_loop, daemon=True)

        self.heartbeat_thread.start()
        self.task_sync_thread.start()

    def stop(self):
        """Stop the distributed coordinator"""
        self.running = False
        logger.log("INFO", "DistributedCoordinator", f"Stopping distributed coordinator {self.coordinator_id}")

        # Wait for threads to finish
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        if self.task_sync_thread:
            self.task_sync_thread.join(timeout=5)

    def register_node(self, node_config: Dict[str, Any]) -> str:
        """Register a new node with the distributed swarm"""
        node_id = node_config.get('node_id') or f"node_{uuid.uuid4().hex[:8]}"

        node = SwarmNode(
            node_id=node_id,
            host=node_config['host'],
            port=node_config['port'],
            status="online",
            capabilities=node_config.get('capabilities', []),
            region=node_config.get('region', 'default'),
            zone=node_config.get('zone', 'default'),
            tags=node_config.get('tags', {})
        )

        self.nodes[node_id] = node

        # Add to cluster
        cluster_id = node_config.get('cluster_id', 'default')
        if cluster_id not in self.clusters:
            self.create_cluster(cluster_id, f"Cluster {cluster_id}")

        if node_id not in self.clusters[cluster_id].nodes:
            self.clusters[cluster_id].nodes.append(node_id)

        # Update heartbeat
        node.last_heartbeat = time.time()

        logger.log("INFO", "DistributedCoordinator", f"Registered node {node_id} in cluster {cluster_id}")
        return node_id

    def unregister_node(self, node_id: str):
        """Unregister a node from the distributed swarm"""
        if node_id in self.nodes:
            # Reassign tasks from this node
            self._reassign_node_tasks(node_id)

            # Remove from clusters
            for cluster in self.clusters.values():
                if node_id in cluster.nodes:
                    cluster.nodes.remove(node_id)
                if cluster.primary_node == node_id:
                    cluster.primary_node = None
                if node_id in cluster.backup_nodes:
                    cluster.backup_nodes.remove(node_id)

            # Remove node
            del self.nodes[node_id]
            del self.node_tasks[node_id]

            logger.log("INFO", "DistributedCoordinator", f"Unregistered node {node_id}")

    def create_cluster(self, cluster_id: str, name: str, config: Dict[str, Any] = None) -> str:
        """Create a new cluster"""
        if cluster_id in self.clusters:
            raise ValueError(f"Cluster {cluster_id} already exists")

        cluster = ClusterConfig(
            cluster_id=cluster_id,
            name=name,
            load_balancing_strategy=config.get('load_balancing_strategy', 'round_robin') if config else 'round_robin',
            failover_enabled=config.get('failover_enabled', True) if config else True,
            auto_scaling_enabled=config.get('auto_scaling_enabled', False) if config else False,
            min_nodes=config.get('min_nodes', 1) if config else 1,
            max_nodes=config.get('max_nodes', 10) if config else 10,
            region=config.get('region', 'default') if config else 'default',
            tags=config.get('tags', {}) if config else {}
        )

        self.clusters[cluster_id] = cluster
        logger.log("INFO", "DistributedCoordinator", f"Created cluster {cluster_id}: {name}")
        return cluster_id

    def submit_task(self, task_config: Dict[str, Any]) -> str:
        """Submit a task to the distributed swarm"""
        task_id = task_config.get('task_id') or f"task_{uuid.uuid4().hex[:12]}"

        task = DistributedTask(
            task_id=task_id,
            description=task_config['description'],
            priority=task_config.get('priority', 1),
            requirements=task_config.get('requirements', {}),
            max_retries=task_config.get('max_retries', 3),
            tags=task_config.get('tags', {})
        )

        self.tasks[task_id] = task

        # Try to assign task immediately
        assigned_node = self.load_balancer.assign_task(task)
        if assigned_node:
            self._assign_task_to_node(task, assigned_node)

        logger.log("INFO", "DistributedCoordinator", f"Submitted task {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a distributed task"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            'task_id': task.task_id,
            'status': task.status,
            'assigned_node': task.assigned_node,
            'priority': task.priority,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'execution_time': task.execution_time(),
            'total_time': task.total_time(),
            'retry_count': task.retry_count,
            'result': task.result
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a distributed task"""
        task = self.tasks.get(task_id)
        if not task or task.status in ['completed', 'failed']:
            return False

        task.status = 'cancelled'
        task.completed_at = time.time()

        # Notify assigned node if any
        if task.assigned_node:
            self._send_node_message(task.assigned_node, {
                'type': 'task_cancel',
                'task_id': task_id
            })

        logger.log("INFO", "DistributedCoordinator", f"Cancelled task {task_id}")
        return True

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all clusters and nodes"""
        cluster_status = {}

        for cluster_id, cluster in self.clusters.items():
            nodes_status = {}
            healthy_nodes = 0
            total_load = 0

            for node_id in cluster.nodes:
                node = self.nodes.get(node_id)
                if node:
                    node_status = {
                        'status': node.status,
                        'healthy': node.is_healthy(),
                        'load_factor': node.load_factor,
                        'agent_count': node.agent_count,
                        'memory_usage': node.memory_usage,
                        'cpu_usage': node.cpu_usage,
                        'network_latency': node.network_latency,
                        'last_heartbeat': node.last_heartbeat,
                        'task_count': len(self.node_tasks.get(node_id, set()))
                    }
                    nodes_status[node_id] = node_status

                    if node.is_healthy():
                        healthy_nodes += 1
                        total_load += node.load_factor

            avg_load = total_load / healthy_nodes if healthy_nodes > 0 else 0

            cluster_status[cluster_id] = {
                'name': cluster.name,
                'node_count': len(cluster.nodes),
                'healthy_nodes': healthy_nodes,
                'average_load': avg_load,
                'primary_node': cluster.primary_node,
                'load_balancing_strategy': cluster.load_balancing_strategy,
                'nodes': nodes_status
            }

        return {
            'coordinator_id': self.coordinator_id,
            'total_nodes': len(self.nodes),
            'total_clusters': len(self.clusters),
            'active_tasks': len([t for t in self.tasks.values() if t.status in ['assigned', 'running']]),
            'pending_tasks': len([t for t in self.tasks.values() if t.status == 'pending']),
            'clusters': cluster_status,
            'timestamp': time.time()
        }

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all nodes and clusters"""
        if not self.nodes:
            return {}

        total_memory = sum(node.memory_usage for node in self.nodes.values())
        total_cpu = sum(node.cpu_usage for node in self.nodes.values())
        total_load = sum(node.load_factor for node in self.nodes.values())
        total_agents = sum(node.agent_count for node in self.nodes.values())

        healthy_nodes = sum(1 for node in self.nodes.values() if node.is_healthy())
        avg_latency = sum(node.network_latency for node in self.nodes.values()) / len(self.nodes)

        # Task metrics
        completed_tasks = len([t for t in self.tasks.values() if t.status == 'completed'])
        failed_tasks = len([t for t in self.tasks.values() if t.status == 'failed'])
        avg_execution_time = sum(
            t.execution_time() for t in self.tasks.values()
            if t.execution_time() is not None
        ) / max(1, completed_tasks)

        return {
            'node_metrics': {
                'total_nodes': len(self.nodes),
                'healthy_nodes': healthy_nodes,
                'health_percentage': (healthy_nodes / len(self.nodes)) * 100 if self.nodes else 0,
                'average_load': total_load / len(self.nodes),
                'average_memory_usage': total_memory / len(self.nodes),
                'average_cpu_usage': total_cpu / len(self.nodes),
                'average_latency': avg_latency,
                'total_agents': total_agents
            },
            'task_metrics': {
                'total_tasks': len(self.tasks),
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': (completed_tasks / max(1, completed_tasks + failed_tasks)) * 100,
                'average_execution_time': avg_execution_time,
                'pending_tasks': len([t for t in self.tasks.values() if t.status == 'pending']),
                'running_tasks': len([t for t in self.tasks.values() if t.status == 'running'])
            },
            'cluster_metrics': {
                'total_clusters': len(self.clusters),
                'nodes_per_cluster': len(self.nodes) / max(1, len(self.clusters))
            },
            'timestamp': time.time()
        }

    def _assign_task_to_node(self, task: DistributedTask, node_id: str):
        """Assign a task to a specific node"""
        task.assigned_node = node_id
        task.status = 'assigned'
        task.started_at = time.time()

        self.node_tasks[node_id].add(task.task_id)

        # Send assignment message to node
        self._send_node_message(node_id, {
            'type': 'task_assign',
            'task_id': task.task_id,
            'description': task.description,
            'priority': task.priority,
            'requirements': task.requirements
        })

        logger.log("INFO", "DistributedCoordinator", f"Assigned task {task.task_id} to node {node_id}")

    def _reassign_node_tasks(self, node_id: str):
        """Reassign all tasks from a failed node"""
        task_ids = list(self.node_tasks.get(node_id, set()))

        for task_id in task_ids:
            task = self.tasks.get(task_id)
            if task and task.status in ['assigned', 'running']:
                # Try to reassign to another node
                new_node = self.load_balancer.assign_task(task)
                if new_node:
                    self._assign_task_to_node(task, new_node)
                    logger.log("WARNING", "DistributedCoordinator", f"Reassigned task {task_id} from {node_id} to {new_node}")
                else:
                    task.status = 'pending'
                    task.assigned_node = None
                    logger.log("ERROR", "DistributedCoordinator", f"Could not reassign task {task_id} from failed node {node_id}")

    def _send_node_message(self, node_id: str, message: Dict[str, Any]):
        """Send a message to a specific node"""
        node = self.nodes.get(node_id)
        if not node:
            return

        # In a real implementation, this would send via network
        # For now, add to message queue for processing
        self.message_queue.append({
            'target_node': node_id,
            'message': message,
            'timestamp': time.time()
        })

    def _heartbeat_loop(self):
        """Background thread for heartbeat monitoring"""
        while self.running:
            try:
                current_time = time.time()

                # Check for node timeouts
                for node_id, node in list(self.nodes.items()):
                    time_since_heartbeat = current_time - node.last_heartbeat

                    if time_since_heartbeat > 60:  # 1 minute timeout
                        if node.status != 'offline':
                            node.status = 'offline'
                            logger.log("WARNING", "DistributedCoordinator", f"Node {node_id} went offline")
                            self._reassign_node_tasks(node_id)
                    elif time_since_heartbeat > 30:  # 30 second grace period
                        if node.status != 'degraded':
                            node.status = 'degraded'
                            logger.log("WARNING", "DistributedCoordinator", f"Node {node_id} degraded")

                # Send heartbeats to nodes (in real implementation)
                # This would be actual network communication

            except Exception as e:
                logger.log("ERROR", "DistributedCoordinator", f"Error in heartbeat loop: {str(e)}")

            time.sleep(self.heartbeat_interval)

    def _task_sync_loop(self):
        """Background thread for task synchronization"""
        while self.running:
            try:
                # Check for pending tasks that need assignment
                pending_tasks = [t for t in self.tasks.values() if t.status == 'pending']
                for task in pending_tasks:
                    assigned_node = self.load_balancer.assign_task(task)
                    if assigned_node:
                        self._assign_task_to_node(task, assigned_node)

                # Check for stuck tasks (running too long)
                running_tasks = [t for t in self.tasks.values() if t.status == 'running']
                for task in running_tasks:
                    if task.started_at and (time.time() - task.started_at) > 3600:  # 1 hour timeout
                        logger.log("WARNING", "DistributedCoordinator", f"Task {task.task_id} running too long, marking as failed")
                        task.status = 'failed'
                        task.completed_at = time.time()

                        # Try to retry if under max retries
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            task.status = 'pending'
                            task.assigned_node = None
                            logger.log("INFO", "DistributedCoordinator", f"Retrying task {task.task_id} (attempt {task.retry_count})")

            except Exception as e:
                logger.log("ERROR", "DistributedCoordinator", f"Error in task sync loop: {str(e)}")

            time.sleep(self.task_sync_interval)

    def handle_node_message(self, node_id: str, message: Dict[str, Any]):
        """Handle incoming message from a node"""
        message_type = message.get('type')

        if message_type == 'heartbeat':
            self._handle_heartbeat(node_id, message)
        elif message_type == 'task_complete':
            self._handle_task_complete(node_id, message)
        elif message_type == 'task_failed':
            self._handle_task_failed(node_id, message)
        elif message_type == 'node_status':
            self._handle_node_status(node_id, message)

    def _handle_heartbeat(self, node_id: str, message: Dict[str, Any]):
        """Handle heartbeat message from node"""
        node = self.nodes.get(node_id)
        if node:
            node.last_heartbeat = time.time()
            node.status = 'online'

            # Update node metrics
            node.load_factor = message.get('load_factor', node.load_factor)
            node.memory_usage = message.get('memory_usage', node.memory_usage)
            node.cpu_usage = message.get('cpu_usage', node.cpu_usage)
            node.agent_count = message.get('agent_count', node.agent_count)

    def _handle_task_complete(self, node_id: str, message: Dict[str, Any]):
        """Handle task completion message from node"""
        task_id = message.get('task_id')
        result = message.get('result')

        task = self.tasks.get(task_id)
        if task:
            task.status = 'completed'
            task.completed_at = time.time()
            task.result = result

            # Remove from node's task list
            self.node_tasks[node_id].discard(task_id)

            logger.log("INFO", "DistributedCoordinator", f"Task {task_id} completed on node {node_id}")

    def _handle_task_failed(self, node_id: str, message: Dict[str, Any]):
        """Handle task failure message from node"""
        task_id = message.get('task_id')
        error = message.get('error', 'Unknown error')

        task = self.tasks.get(task_id)
        if task:
            # Try to retry if under max retries
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = 'pending'
                task.assigned_node = None
                logger.log("WARNING", "DistributedCoordinator", f"Task {task_id} failed on node {node_id}, retrying (attempt {task.retry_count}): {error}")
            else:
                task.status = 'failed'
                task.completed_at = time.time()
                logger.log("ERROR", "DistributedCoordinator", f"Task {task_id} failed permanently on node {node_id}: {error}")

            # Remove from node's task list
            self.node_tasks[node_id].discard(task_id)

    def _handle_node_status(self, node_id: str, message: Dict[str, Any]):
        """Handle node status update"""
        node = self.nodes.get(node_id)
        if node:
            # Update all node metrics
            for key, value in message.items():
                if key != 'type' and hasattr(node, key):
                    setattr(node, key, value)

class DistributedLoadBalancer:
    """Load balancer for distributed swarm"""

    def __init__(self, coordinator: DistributedCoordinator):
        self.coordinator = coordinator

    def assign_task(self, task: DistributedTask) -> Optional[str]:
        """Assign a task to the best available node"""
        available_nodes = self._get_available_nodes()

        if not available_nodes:
            return None

        # Choose assignment strategy based on task requirements
        strategy = self._determine_strategy(task)

        if strategy == 'capability_based':
            return self._assign_by_capability(task, available_nodes)
        elif strategy == 'least_loaded':
            return self._assign_least_loaded(available_nodes)
        else:  # round_robin
            return self._assign_round_robin(available_nodes)

    def _get_available_nodes(self) -> List[SwarmNode]:
        """Get list of available (healthy) nodes"""
        return [node for node in self.coordinator.nodes.values() if node.is_healthy()]

    def _determine_strategy(self, task: DistributedTask) -> str:
        """Determine the best assignment strategy for a task"""
        requirements = task.requirements

        # If task has specific capability requirements, use capability-based assignment
        if requirements.get('required_capabilities'):
            return 'capability_based'

        # If task is high priority or time-sensitive, use least loaded
        if task.priority >= 4 or requirements.get('time_sensitive'):
            return 'least_loaded'

        # Default to round robin for load distribution
        return 'round_robin'

    def _assign_by_capability(self, task: DistributedTask, nodes: List[SwarmNode]) -> Optional[str]:
        """Assign task based on required capabilities"""
        required_caps = set(task.requirements.get('required_capabilities', []))

        # Find nodes that have all required capabilities
        suitable_nodes = []
        for node in nodes:
            node_caps = set(node.capabilities)
            if required_caps.issubset(node_caps):
                suitability_score = len(required_caps.intersection(node_caps)) / len(required_caps)
                health_score = node.get_health_score()
                combined_score = suitability_score * 0.7 + health_score * 0.3
                suitable_nodes.append((node.node_id, combined_score))

        if suitable_nodes:
            # Return node with highest suitability score
            suitable_nodes.sort(key=lambda x: x[1], reverse=True)
            return suitable_nodes[0][0]

        return None

    def _assign_least_loaded(self, nodes: List[SwarmNode]) -> Optional[str]:
        """Assign to the least loaded healthy node"""
        if not nodes:
            return None

        # Sort by combined load factor and health score
        node_scores = []
        for node in nodes:
            # Lower load factor is better, higher health score is better
            load_score = 1.0 - node.load_factor  # Invert so higher is better
            health_score = node.get_health_score()
            combined_score = load_score * 0.6 + health_score * 0.4
            node_scores.append((node.node_id, combined_score))

        node_scores.sort(key=lambda x: x[1], reverse=True)
        return node_scores[0][0]

    def _assign_round_robin(self, nodes: List[SwarmNode]) -> Optional[str]:
        """Assign using round-robin strategy"""
        if not nodes:
            return None

        # Simple round-robin based on node ID hash and current time
        # In a real implementation, you'd maintain a counter per cluster
        current_time = int(time.time())
        node_index = current_time % len(nodes)
        return nodes[node_index].node_id

class SwarmHealthMonitor:
    """Health monitoring for distributed swarm"""

    def __init__(self, coordinator: DistributedCoordinator):
        self.coordinator = coordinator
        self.health_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.alerts: List[Dict[str, Any]] = []

    def check_cluster_health(self) -> Dict[str, Any]:
        """Check overall cluster health"""
        health_status = {
            'overall_health': 'healthy',
            'issues': [],
            'recommendations': []
        }

        total_nodes = len(self.coordinator.nodes)
        healthy_nodes = sum(1 for node in self.coordinator.nodes.values() if node.is_healthy())

        if healthy_nodes < total_nodes * 0.8:  # Less than 80% healthy
            health_status['overall_health'] = 'critical'
            health_status['issues'].append(f"Only {healthy_nodes}/{total_nodes} nodes are healthy")
            health_status['recommendations'].append("Consider scaling up or investigating node failures")

        # Check for overloaded nodes
        overloaded_nodes = [node for node in self.coordinator.nodes.values()
                          if node.load_factor > 0.9 and node.is_healthy()]

        if overloaded_nodes:
            health_status['issues'].append(f"{len(overloaded_nodes)} nodes are overloaded")
            health_status['recommendations'].append("Consider redistributing load or adding capacity")

        # Check for high latency
        high_latency_nodes = [node for node in self.coordinator.nodes.values()
                            if node.network_latency > 500 and node.is_healthy()]

        if high_latency_nodes:
            health_status['issues'].append(f"{len(high_latency_nodes)} nodes have high network latency")
            health_status['recommendations'].append("Investigate network connectivity issues")

        return health_status

class AutoScaler:
    """Auto-scaling for distributed swarm"""

    def __init__(self, coordinator: DistributedCoordinator):
        self.coordinator = coordinator
        self.scaling_history: List[Dict[str, Any]] = []
        self.last_scaling_check = 0
        self.scaling_cooldown = 300  # 5 minutes between scaling actions

    def check_scaling_needed(self) -> Optional[Dict[str, Any]]:
        """Check if scaling is needed"""
        current_time = time.time()
        if current_time - self.last_scaling_check < self.scaling_cooldown:
            return None

        self.last_scaling_check = current_time

        # Check each cluster
        for cluster_id, cluster in self.coordinator.clusters.items():
            if not cluster.auto_scaling_enabled:
                continue

            healthy_nodes = sum(1 for node_id in cluster.nodes
                              if node_id in self.coordinator.nodes and
                              self.coordinator.nodes[node_id].is_healthy())

            avg_load = sum(self.coordinator.nodes[node_id].load_factor
                          for node_id in cluster.nodes
                          if node_id in self.coordinator.nodes) / max(1, len(cluster.nodes))

            # Scale up conditions
            if healthy_nodes >= cluster.min_nodes and avg_load > 0.8 and healthy_nodes < cluster.max_nodes:
                return {
                    'action': 'scale_up',
                    'cluster_id': cluster_id,
                    'reason': f"High load ({avg_load:.1%}) with room to scale",
                    'target_nodes': min(healthy_nodes + 1, cluster.max_nodes)
                }

            # Scale down conditions
            elif healthy_nodes > cluster.min_nodes and avg_load < 0.3:
                return {
                    'action': 'scale_down',
                    'cluster_id': cluster_id,
                    'reason': f"Low load ({avg_load:.1%}) with excess capacity",
                    'target_nodes': max(healthy_nodes - 1, cluster.min_nodes)
                }

        return None

# Global distributed coordinator instance
distributed_coordinator = DistributedCoordinator()

# Integration functions
def initialize_distributed_swarm(coordinator_id: str = None) -> DistributedCoordinator:
    """Initialize the distributed swarm coordinator"""
    global distributed_coordinator
    distributed_coordinator = DistributedCoordinator(coordinator_id)
    distributed_coordinator.start()
    return distributed_coordinator

def register_swarm_node(node_config: Dict[str, Any]) -> str:
    """Register a new node with the distributed swarm"""
    return distributed_coordinator.register_node(node_config)

def submit_distributed_task(task_config: Dict[str, Any]) -> str:
    """Submit a task to the distributed swarm"""
    return distributed_coordinator.submit_task(task_config)

def get_distributed_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a distributed task"""
    return distributed_coordinator.get_task_status(task_id)

def get_swarm_cluster_status() -> Dict[str, Any]:
    """Get comprehensive status of all clusters and nodes"""
    return distributed_coordinator.get_cluster_status()

def get_swarm_aggregated_metrics() -> Dict[str, Any]:
    """Get aggregated metrics across all nodes and clusters"""
    return distributed_coordinator.get_aggregated_metrics()

def shutdown_distributed_swarm():
    """Shutdown the distributed swarm coordinator"""
    distributed_coordinator.stop()