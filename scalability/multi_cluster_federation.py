"""
Multi-Cluster Federation with Horizontal Scaling
Provides cross-cluster communication, load balancing, and resource optimization
"""

import asyncio
import time
import hashlib
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import statistics

from ..core.base import logger
from ..federation.federation import FederationManager, SharedTask, MemorySync, AnalyticsData
from ..discovery import SwarmMetadata


class ClusterRole(Enum):
    """Roles a cluster can have in federation"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EDGE = "edge"
    SPECIALIZED = "specialized"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    GEOGRAPHIC = "geographic"


@dataclass
class ClusterNode:
    """Represents a node in the multi-cluster federation"""
    cluster_id: str
    node_id: str
    role: ClusterRole
    capabilities: Set[str]
    load_metrics: Dict[str, Any] = field(default_factory=dict)
    location: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    active_tasks: int = 0
    max_capacity: int = 100

    @property
    def utilization(self) -> float:
        """Calculate current utilization"""
        return (self.active_tasks / self.max_capacity) * 100 if self.max_capacity > 0 else 0

    @property
    def available_capacity(self) -> int:
        """Calculate available capacity"""
        return max(0, self.max_capacity - self.active_tasks)

    def is_healthy(self) -> bool:
        """Check if node is healthy"""
        return time.time() - self.last_heartbeat < 60  # 60 seconds timeout


@dataclass
class ClusterGroup:
    """Represents a group of clusters with shared responsibilities"""
    group_id: str
    clusters: Set[str]
    primary_cluster: str
    capabilities: Set[str]
    load_distribution: Dict[str, float] = field(default_factory=dict)

    def get_least_loaded_cluster(self, cluster_nodes: Dict[str, List[ClusterNode]]) -> Optional[str]:
        """Get the least loaded cluster in this group"""
        lowest_load = float('inf')
        selected_cluster = None

        for cluster_id in self.clusters:
            if cluster_id not in cluster_nodes:
                continue

            nodes = cluster_nodes[cluster_id]
            if not nodes:
                continue

            # Calculate average utilization for cluster
            avg_utilization = sum(node.utilization for node in nodes) / len(nodes)

            if avg_utilization < lowest_load:
                lowest_load = avg_utilization
                selected_cluster = cluster_id

        return selected_cluster


class MultiClusterFederationManager:
    """
    Enhanced federation manager supporting multi-cluster topologies,
    horizontal scaling, and intelligent load balancing
    """

    def __init__(self,
                 local_cluster_id: str,
                 local_node_id: str,
                 federation_config: Optional[Dict[str, Any]] = None):
        self.local_cluster_id = local_cluster_id
        self.local_node_id = local_node_id
        self.config = federation_config or self._get_default_config()

        # Core components
        self.federation_manager = FederationManager(
            local_swarm_id=local_cluster_id,
            auth_token=self.config["auth_token"]
        )

        # Multi-cluster state
        self.cluster_nodes: Dict[str, List[ClusterNode]] = {}
        self.cluster_groups: Dict[str, ClusterGroup] = {}
        self.cluster_topology: Dict[str, Set[str]] = {}  # cluster -> connected clusters

        # Load balancing
        self.load_balancing_strategy = LoadBalancingStrategy(self.config["load_balancing"]["strategy"])
        self.task_distribution_history: Dict[str, str] = {}  # task_id -> assigned_cluster

        # Scaling and optimization
        self.scaling_policies: Dict[str, Dict[str, Any]] = {}
        self.resource_pools: Dict[str, Dict[str, Any]] = {}

        # Monitoring
        self.performance_metrics: Dict[str, List[float]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._scaling_task: Optional[asyncio.Task] = None

        logger.info(f"MultiClusterFederationManager initialized for cluster {local_cluster_id}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "auth_token": "federation-token-123",
            "load_balancing": {
                "strategy": "least_loaded",
                "rebalance_interval": 60,
                "overload_threshold": 80,
                "underload_threshold": 20
            },
            "scaling": {
                "auto_scale": True,
                "max_clusters_per_group": 10,
                "min_clusters_per_group": 1,
                "scale_up_threshold": 85,
                "scale_down_threshold": 15
            },
            "topology": {
                "max_hops": 3,
                "preferred_connections": 5,
                "reconnect_interval": 30
            },
            "monitoring": {
                "metrics_interval": 30,
                "health_check_interval": 60,
                "performance_window": 300  # 5 minutes
            }
        }

    async def start_multi_cluster_federation(self):
        """Start the multi-cluster federation"""
        logger.info("Starting multi-cluster federation...")

        # Start base federation
        await self.federation_manager.start_federation()

        # Register local cluster
        self._register_local_cluster()

        # Start monitoring and scaling tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._scaling_task = asyncio.create_task(self._scaling_loop())

        logger.info("Multi-cluster federation started")

    async def stop_multi_cluster_federation(self):
        """Stop the multi-cluster federation"""
        logger.info("Stopping multi-cluster federation...")

        # Stop monitoring tasks
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        if self._scaling_task and not self._scaling_task.done():
            self._scaling_task.cancel()

        # Stop base federation
        await self.federation_manager.stop_federation()

        logger.info("Multi-cluster federation stopped")

    def _register_local_cluster(self):
        """Register the local cluster in the federation"""
        local_node = ClusterNode(
            cluster_id=self.local_cluster_id,
            node_id=self.local_node_id,
            role=ClusterRole.PRIMARY,
            capabilities={"task_processing", "memory_sync", "analytics"},
            max_capacity=self.config.get("local_capacity", 100)
        )

        self.cluster_nodes[self.local_cluster_id] = [local_node]
        self.cluster_topology[self.local_cluster_id] = set()

    async def register_remote_cluster(self, cluster_metadata: SwarmMetadata, capabilities: Set[str]):
        """Register a remote cluster in the federation"""
        cluster_id = cluster_metadata.swarm_id

        # Create cluster node
        node = ClusterNode(
            cluster_id=cluster_id,
            node_id=f"{cluster_id}_node_1",  # Simplified - would be more complex in real implementation
            role=self._determine_cluster_role(capabilities),
            capabilities=capabilities,
            location=getattr(cluster_metadata, 'location', None),
            max_capacity=getattr(cluster_metadata, 'capacity', 50)
        )

        self.cluster_nodes[cluster_id] = [node]
        self.cluster_topology[cluster_id] = {self.local_cluster_id}

        # Update local topology
        self.cluster_topology[self.local_cluster_id].add(cluster_id)

        # Connect via federation manager
        await self.federation_manager.connection_manager.connect_to_swarm(cluster_metadata)

        logger.info(f"Registered remote cluster: {cluster_id} with role {node.role.value}")

    def _determine_cluster_role(self, capabilities: Set[str]) -> ClusterRole:
        """Determine the role of a cluster based on its capabilities"""
        if "high_performance" in capabilities:
            return ClusterRole.PRIMARY
        elif "specialized_processing" in capabilities:
            return ClusterRole.SPECIALIZED
        elif "edge_computing" in capabilities:
            return ClusterRole.EDGE
        else:
            return ClusterRole.SECONDARY

    async def distribute_task_multi_cluster(self, task: SharedTask) -> Optional[str]:
        """
        Distribute a task across the multi-cluster federation using intelligent load balancing
        """
        # Find best cluster for the task
        target_cluster = await self._select_optimal_cluster(task)

        if not target_cluster or target_cluster == self.local_cluster_id:
            # Process locally
            return None

        # Distribute to remote cluster
        success = await self.federation_manager.share_task(task, [target_cluster])

        if success:
            self.task_distribution_history[task.task_id] = target_cluster
            logger.info(f"Distributed task {task.task_id} to cluster {target_cluster}")
            return target_cluster

        return None

    async def _select_optimal_cluster(self, task: SharedTask) -> Optional[str]:
        """Select the optimal cluster for a task based on load balancing strategy"""
        if self.load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._find_least_loaded_cluster(task)
        elif self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._find_round_robin_cluster()
        elif self.load_balancing_strategy == LoadBalancingStrategy.WEIGHTED:
            return self._find_weighted_cluster(task)
        elif self.load_balancing_strategy == LoadBalancingStrategy.GEOGRAPHIC:
            return self._find_geographic_cluster(task)
        else:
            return self._find_least_loaded_cluster(task)

    def _find_least_loaded_cluster(self, task: SharedTask) -> Optional[str]:
        """Find the least loaded cluster that can handle the task"""
        lowest_load = float('inf')
        selected_cluster = None

        for cluster_id, nodes in self.cluster_nodes.items():
            if not nodes:
                continue

            # Check if cluster can handle task type
            if not self._cluster_can_handle_task(cluster_id, task):
                continue

            # Calculate average utilization
            avg_utilization = sum(node.utilization for node in nodes) / len(nodes)

            if avg_utilization < lowest_load:
                lowest_load = avg_utilization
                selected_cluster = cluster_id

        return selected_cluster

    def _find_round_robin_cluster(self) -> Optional[str]:
        """Find next cluster using round-robin distribution"""
        available_clusters = [cid for cid in self.cluster_nodes.keys() if cid != self.local_cluster_id]

        if not available_clusters:
            return None

        # Simple round-robin based on current time
        index = int(time.time() / 60) % len(available_clusters)  # Change every minute
        return available_clusters[index]

    def _find_weighted_cluster(self, task: SharedTask) -> Optional[str]:
        """Find cluster using weighted load balancing"""
        candidates = []

        for cluster_id, nodes in self.cluster_nodes.items():
            if not nodes or not self._cluster_can_handle_task(cluster_id, task):
                continue

            # Calculate weight based on capacity and current load
            total_capacity = sum(node.max_capacity for node in nodes)
            total_load = sum(node.active_tasks for node in nodes)
            utilization = total_load / total_capacity if total_capacity > 0 else 1

            # Weight = capacity * (1 - utilization) - higher capacity and lower utilization = higher weight
            weight = total_capacity * (1 - utilization)
            candidates.append((cluster_id, weight))

        if not candidates:
            return None

        # Select cluster with highest weight
        return max(candidates, key=lambda x: x[1])[0]

    def _find_geographic_cluster(self, task: SharedTask) -> Optional[str]:
        """Find cluster based on geographic location (simplified)"""
        # This would use actual geographic data in a real implementation
        # For now, prefer local cluster for latency-sensitive tasks
        if task.task_type in ["real_time", "interactive"]:
            return self.local_cluster_id

        return self._find_least_loaded_cluster(task)

    def _cluster_can_handle_task(self, cluster_id: str, task: SharedTask) -> bool:
        """Check if a cluster can handle a specific task"""
        if cluster_id not in self.cluster_nodes:
            return False

        nodes = self.cluster_nodes[cluster_id]
        if not nodes:
            return False

        # Check capabilities
        required_capability = self._get_task_capability_requirement(task)
        cluster_capabilities = set()
        for node in nodes:
            cluster_capabilities.update(node.capabilities)

        return required_capability in cluster_capabilities

    def _get_task_capability_requirement(self, task: SharedTask) -> str:
        """Get the capability required for a task"""
        task_type_mapping = {
            "analysis": "task_processing",
            "computation": "computation",
            "memory_heavy": "memory_intensive",
            "io_bound": "io_processing",
            "real_time": "real_time_processing"
        }

        return task_type_mapping.get(task.task_type, "task_processing")

    async def _monitoring_loop(self):
        """Continuous monitoring of cluster health and performance"""
        while True:
            try:
                await asyncio.sleep(self.config["monitoring"]["metrics_interval"])

                # Update cluster metrics
                await self._update_cluster_metrics()

                # Check cluster health
                await self._check_cluster_health()

                # Update performance metrics
                self._update_performance_metrics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _update_cluster_metrics(self):
        """Update metrics for all clusters"""
        for cluster_id, nodes in self.cluster_nodes.items():
            # In a real implementation, this would query each cluster for metrics
            # For now, simulate with basic updates
            for node in nodes:
                # Update heartbeat
                if cluster_id == self.local_cluster_id:
                    node.last_heartbeat = time.time()
                else:
                    # Simulate remote cluster heartbeat (would come via federation messages)
                    pass

    async def _check_cluster_health(self):
        """Check health of all clusters"""
        unhealthy_clusters = []

        for cluster_id, nodes in self.cluster_nodes.items():
            healthy_nodes = sum(1 for node in nodes if node.is_healthy())

            if healthy_nodes == 0:
                unhealthy_clusters.append(cluster_id)
                logger.warning(f"Cluster {cluster_id} has no healthy nodes")

        # Handle unhealthy clusters (reconnect, failover, etc.)
        for cluster_id in unhealthy_clusters:
            await self._handle_unhealthy_cluster(cluster_id)

    async def _handle_unhealthy_cluster(self, cluster_id: str):
        """Handle an unhealthy cluster"""
        # Redistribute tasks from unhealthy cluster
        affected_tasks = [task_id for task_id, assigned_cluster in self.task_distribution_history.items()
                         if assigned_cluster == cluster_id]

        for task_id in affected_tasks:
            # Find new cluster for task
            # This is simplified - would need actual task data
            new_cluster = self._find_least_loaded_cluster(None)
            if new_cluster:
                self.task_distribution_history[task_id] = new_cluster
                logger.info(f"Redistributed task {task_id} from {cluster_id} to {new_cluster}")

    def _update_performance_metrics(self):
        """Update performance metrics for monitoring"""
        current_time = time.time()

        # Track response times, throughput, etc.
        # This would collect actual metrics in a real implementation
        pass

    async def _scaling_loop(self):
        """Automatic scaling based on load and policies"""
        if not self.config["scaling"]["auto_scale"]:
            return

        while True:
            try:
                await asyncio.sleep(self.config["load_balancing"]["rebalance_interval"])

                # Check for scaling opportunities
                await self._evaluate_scaling_decisions()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")

    async def _evaluate_scaling_decisions(self):
        """Evaluate and execute scaling decisions"""
        for group_id, group in self.cluster_groups.items():
            # Check if group needs scaling
            total_load = self._calculate_group_load(group)
            total_capacity = self._calculate_group_capacity(group)

            if total_capacity == 0:
                continue

            utilization = (total_load / total_capacity) * 100

            if utilization > self.config["scaling"]["scale_up_threshold"]:
                await self._scale_up_group(group)
            elif utilization < self.config["scaling"]["scale_down_threshold"]:
                await self._scale_down_group(group)

    def _calculate_group_load(self, group: ClusterGroup) -> float:
        """Calculate total load for a cluster group"""
        total_load = 0
        for cluster_id in group.clusters:
            if cluster_id in self.cluster_nodes:
                nodes = self.cluster_nodes[cluster_id]
                total_load += sum(node.active_tasks for node in nodes)
        return total_load

    def _calculate_group_capacity(self, group: ClusterGroup) -> float:
        """Calculate total capacity for a cluster group"""
        total_capacity = 0
        for cluster_id in group.clusters:
            if cluster_id in self.cluster_nodes:
                nodes = self.cluster_nodes[cluster_id]
                total_capacity += sum(node.max_capacity for node in nodes)
        return total_capacity

    async def _scale_up_group(self, group: ClusterGroup):
        """Scale up a cluster group by adding more clusters"""
        if len(group.clusters) >= self.config["scaling"]["max_clusters_per_group"]:
            return

        logger.info(f"Scaling up cluster group {group.group_id}")

        # In a real implementation, this would provision new clusters
        # For now, just log the scaling decision
        pass

    async def _scale_down_group(self, group: ClusterGroup):
        """Scale down a cluster group by removing clusters"""
        if len(group.clusters) <= self.config["scaling"]["min_clusters_per_group"]:
            return

        logger.info(f"Scaling down cluster group {group.group_id}")

        # Find least utilized cluster to remove
        least_utilized = None
        lowest_utilization = float('inf')

        for cluster_id in group.clusters:
            if cluster_id in self.cluster_nodes:
                nodes = self.cluster_nodes[cluster_id]
                avg_utilization = sum(node.utilization for node in nodes) / len(nodes)

                if avg_utilization < lowest_utilization:
                    lowest_utilization = avg_utilization
                    least_utilized = cluster_id

        if least_utilized:
            # Migrate tasks and remove cluster
            await self._migrate_tasks_from_cluster(least_utilized)
            logger.info(f"Scaled down cluster {least_utilized} from group {group.group_id}")

    async def _migrate_tasks_from_cluster(self, cluster_id: str):
        """Migrate tasks from a cluster being scaled down"""
        tasks_to_migrate = [task_id for task_id, assigned_cluster in self.task_distribution_history.items()
                           if assigned_cluster == cluster_id]

        for task_id in tasks_to_migrate:
            # Find new cluster
            new_cluster = self._find_least_loaded_cluster(None)
            if new_cluster:
                self.task_distribution_history[task_id] = new_cluster
                logger.info(f"Migrated task {task_id} from {cluster_id} to {new_cluster}")

    def get_multi_cluster_metrics(self) -> Dict[str, Any]:
        """Get comprehensive multi-cluster metrics"""
        metrics = {
            "federation": self.federation_manager.get_federation_metrics(),
            "clusters": {},
            "topology": dict(self.cluster_topology),
            "load_balancing": {
                "strategy": self.load_balancing_strategy.value,
                "distributed_tasks": len(self.task_distribution_history)
            },
            "scaling": {
                "auto_scale_enabled": self.config["scaling"]["auto_scale"],
                "cluster_groups": len(self.cluster_groups)
            }
        }

        # Add cluster-specific metrics
        for cluster_id, nodes in self.cluster_nodes.items():
            cluster_metrics = {
                "node_count": len(nodes),
                "total_capacity": sum(node.max_capacity for node in nodes),
                "total_load": sum(node.active_tasks for node in nodes),
                "avg_utilization": sum(node.utilization for node in nodes) / len(nodes) if nodes else 0,
                "healthy_nodes": sum(1 for node in nodes if node.is_healthy()),
                "capabilities": list(set(cap for node in nodes for cap in node.capabilities))
            }
            metrics["clusters"][cluster_id] = cluster_metrics

        return metrics

    async def optimize_resource_allocation(self) -> Dict[str, Any]:
        """Perform global resource optimization across clusters"""
        optimization_results = {
            "load_balancing_actions": [],
            "resource_redistribution": [],
            "efficiency_improvements": [],
            "bottleneck_resolutions": []
        }

        # Analyze cluster utilization patterns
        cluster_utilizations = {}
        for cluster_id, nodes in self.cluster_nodes.items():
            if nodes:
                cluster_utilizations[cluster_id] = sum(node.utilization for node in nodes) / len(nodes)

        # Find overloaded and underloaded clusters
        overloaded = [cid for cid, util in cluster_utilizations.items()
                     if util > self.config["load_balancing"]["overload_threshold"]]
        underloaded = [cid for cid, util in cluster_utilizations.items()
                      if util < self.config["load_balancing"]["underload_threshold"]]

        # Generate optimization actions
        for over_cluster in overloaded:
            for under_cluster in underloaded:
                # Suggest task migration
                optimization_results["load_balancing_actions"].append({
                    "action": "migrate_tasks",
                    "from_cluster": over_cluster,
                    "to_cluster": under_cluster,
                    "reason": "load_balancing"
                })

        logger.info(f"Generated {len(optimization_results['load_balancing_actions'])} optimization actions")

        return optimization_results


# Global multi-cluster federation manager
multi_cluster_federation: Optional[MultiClusterFederationManager] = None


async def initialize_multi_cluster_federation(
    local_cluster_id: str,
    local_node_id: str,
    config: Optional[Dict[str, Any]] = None
) -> MultiClusterFederationManager:
    """Initialize the multi-cluster federation manager"""
    global multi_cluster_federation

    multi_cluster_federation = MultiClusterFederationManager(
        local_cluster_id=local_cluster_id,
        local_node_id=local_node_id,
        federation_config=config
    )

    await multi_cluster_federation.start_multi_cluster_federation()

    logger.info(f"Initialized multi-cluster federation for {local_cluster_id}")
    return multi_cluster_federation


async def shutdown_multi_cluster_federation():
    """Shutdown the multi-cluster federation"""
    global multi_cluster_federation

    if multi_cluster_federation:
        await multi_cluster_federation.stop_multi_cluster_federation()
        multi_cluster_federation = None

    logger.info("Multi-cluster federation shutdown complete")