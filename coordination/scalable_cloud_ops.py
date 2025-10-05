from typing import Dict, List, Any, Optional, Tuple, Callable
from .base import logger, metrics
import time
import threading
import psutil
import random
from dataclasses import dataclass, field
from enum import Enum
import statistics
import math
from collections import deque
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class ScalingStrategy(Enum):
    REACTIVE = "reactive"  # Scale based on current metrics
    PREDICTIVE = "predictive"  # Scale based on predicted load
    SCHEDULED = "scheduled"  # Scale based on time-based patterns
    HYBRID = "hybrid"  # Combination of multiple strategies

class ScalingDirection(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_CHANGE = "no_change"

class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    KUBERNETES = "kubernetes"
    DOCKER_SWARM = "docker_swarm"
    LOCAL = "local"

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

@dataclass
class ScalingPolicy:
    """Defines when and how to scale resources"""
    policy_id: str
    name: str
    resource_type: ResourceType
    scaling_strategy: ScalingStrategy
    scale_up_threshold: float  # Percentage (e.g., 80.0 for 80%)
    scale_down_threshold: float  # Percentage (e.g., 20.0 for 20%)
    min_instances: int = 1
    max_instances: int = 100
    cooldown_period: int = 300  # seconds between scaling actions
    evaluation_period: int = 60  # seconds to evaluate metrics
    predictive_window: int = 600  # seconds to look ahead for predictive scaling
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScalingAction:
    """Represents a scaling action to be executed"""
    action_id: str
    policy_id: str
    direction: ScalingDirection
    current_instances: int
    target_instances: int
    reason: str
    timestamp: float = field(default_factory=time.time)
    executed: bool = False
    success: bool = False
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResourceMetrics:
    """Current resource utilization metrics"""
    resource_type: ResourceType
    current_value: float
    max_value: float
    utilization_percent: float
    trend: str  # "increasing", "decreasing", "stable"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkloadPattern:
    """Historical workload patterns for predictive scaling"""
    pattern_id: str
    resource_type: ResourceType
    time_window: int  # seconds
    pattern_type: str  # "daily", "weekly", "seasonal"
    peak_times: List[Tuple[int, int]]  # (hour, minute) tuples
    baseline_utilization: float
    peak_utilization: float
    confidence_score: float
    last_updated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CloudResource:
    """Represents a cloud resource instance"""
    resource_id: str
    resource_type: str
    provider: CloudProvider
    instance_type: str
    region: str
    availability_zone: str
    state: str  # "pending", "running", "stopped", "terminated"
    launch_time: float
    cost_per_hour: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AutoScalingGroup:
    """Manages a group of auto-scaling resources"""
    group_id: str
    name: str
    resource_type: str
    provider: CloudProvider
    min_size: int
    max_size: int
    desired_capacity: int
    current_instances: List[CloudResource] = field(default_factory=list)
    scaling_policies: List[ScalingPolicy] = field(default_factory=list)
    cooldown_until: float = 0
    last_scaling_action: Optional[ScalingAction] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ScalableCloudOps:
    """Manages auto-scaling of agents based on workload spikes"""

    def __init__(self, cloud_provider: CloudProvider = CloudProvider.LOCAL):
        self.cloud_provider = cloud_provider

        # Scaling policies
        self.scaling_policies: Dict[str, ScalingPolicy] = {}
        self.policy_lock = threading.Lock()

        # Auto-scaling groups
        self.auto_scaling_groups: Dict[str, AutoScalingGroup] = {}
        self.group_lock = threading.Lock()

        # Resource metrics
        self.resource_metrics: Dict[ResourceType, deque] = {
            rt: deque(maxlen=1000) for rt in ResourceType
        }
        self.metrics_lock = threading.Lock()

        # Workload patterns
        self.workload_patterns: Dict[str, WorkloadPattern] = {}
        self.pattern_lock = threading.Lock()

        # Scaling actions history
        self.scaling_actions: deque = deque(maxlen=10000)
        self.actions_lock = threading.Lock()

        # Cloud resources
        self.cloud_resources: Dict[str, CloudResource] = {}
        self.resource_lock = threading.Lock()

        # Configuration
        self.metrics_collection_interval = 30  # seconds
        self.scaling_evaluation_interval = 60  # seconds
        self.pattern_analysis_interval = 3600  # 1 hour
        self.max_scaling_actions_per_hour = 10
        self.cost_optimization_enabled = True
        self.predictive_scaling_enabled = True

        # Background threads
        self.metrics_thread: Optional[threading.Thread] = None
        self.scaling_thread: Optional[threading.Thread] = None
        self.pattern_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False

        # Cost tracking
        self.cost_history: deque = deque(maxlen=10000)
        self.cost_lock = threading.Lock()

    def start(self):
        """Start the scalable cloud operations system"""
        logger.log("INFO", "ScalableCloudOps", f"Starting scalable cloud operations with {self.cloud_provider.value} provider")

        self.running = True

        # Start background threads
        self.metrics_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self.scaling_thread = threading.Thread(target=self._evaluate_scaling, daemon=True)
        self.pattern_thread = threading.Thread(target=self._analyze_patterns, daemon=True)
        self.monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)

        self.metrics_thread.start()
        self.scaling_thread.start()
        self.pattern_thread.start()
        self.monitoring_thread.start()

        # Initialize default scaling policies
        self._initialize_default_policies()

        logger.log("INFO", "ScalableCloudOps", "Scalable cloud operations started")

    def stop(self):
        """Stop the scalable cloud operations system"""
        logger.log("INFO", "ScalableCloudOps", f"Stopping scalable cloud operations")

        self.running = False

        # Wait for threads to finish
        threads = [self.metrics_thread, self.scaling_thread, self.pattern_thread, self.monitoring_thread]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=5)

        logger.log("INFO", "ScalableCloudOps", "Scalable cloud operations stopped")

    def create_scaling_policy(self, policy_config: Dict[str, Any]) -> str:
        """Create a new scaling policy"""

        policy_id = policy_config.get('policy_id', f"policy_{int(time.time())}_{random.randint(1000, 9999)}")

        policy = ScalingPolicy(
            policy_id=policy_id,
            name=policy_config.get('name', f'Policy {policy_id}'),
            resource_type=ResourceType(policy_config.get('resource_type', 'cpu')),
            scaling_strategy=ScalingStrategy(policy_config.get('scaling_strategy', 'reactive')),
            scale_up_threshold=policy_config.get('scale_up_threshold', 80.0),
            scale_down_threshold=policy_config.get('scale_down_threshold', 20.0),
            min_instances=policy_config.get('min_instances', 1),
            max_instances=policy_config.get('max_instances', 10),
            cooldown_period=policy_config.get('cooldown_period', 300),
            evaluation_period=policy_config.get('evaluation_period', 60),
            predictive_window=policy_config.get('predictive_window', 600),
            enabled=policy_config.get('enabled', True),
            metadata=policy_config.get('metadata', {})
        )

        with self.policy_lock:
            self.scaling_policies[policy_id] = policy

        logger.log("INFO", "ScalableCloudOps", f"Created scaling policy {policy_id} for {policy.resource_type.value}")
        return policy_id

    def create_auto_scaling_group(self, group_config: Dict[str, Any]) -> str:
        """Create a new auto-scaling group"""

        group_id = group_config.get('group_id', f"group_{int(time.time())}_{random.randint(1000, 9999)}")

        group = AutoScalingGroup(
            group_id=group_id,
            name=group_config.get('name', f'ASG {group_id}'),
            resource_type=group_config.get('resource_type', 'agent'),
            provider=self.cloud_provider,
            min_size=group_config.get('min_size', 1),
            max_size=group_config.get('max_size', 10),
            desired_capacity=group_config.get('desired_capacity', 1),
            scaling_policies=group_config.get('scaling_policies', []),
            metadata=group_config.get('metadata', {})
        )

        with self.group_lock:
            self.auto_scaling_groups[group_id] = group

        # Initialize with minimum instances
        self._scale_group_to_capacity(group, group.min_size)

        logger.log("INFO", "ScalableCloudOps", f"Created auto-scaling group {group_id} with capacity {group.min_size}-{group.max_size}")
        return group_id

    def get_scaling_status(self) -> Dict[str, Any]:
        """Get comprehensive scaling status"""

        with self.group_lock:
            groups_status = {}
            for group_id, group in self.auto_scaling_groups.items():
                groups_status[group_id] = {
                    'name': group.name,
                    'resource_type': group.resource_type,
                    'current_capacity': len(group.current_instances),
                    'desired_capacity': group.desired_capacity,
                    'min_size': group.min_size,
                    'max_size': group.max_size,
                    'cooldown_remaining': max(0, group.cooldown_until - time.time()),
                    'last_scaling_action': group.last_scaling_action.action_id if group.last_scaling_action else None,
                    'policies_count': len(group.scaling_policies)
                }

        with self.metrics_lock:
            latest_metrics = {}
            for resource_type, metrics_queue in self.resource_metrics.items():
                if metrics_queue:
                    latest = metrics_queue[-1]
                    latest_metrics[resource_type.value] = {
                        'utilization_percent': latest.utilization_percent,
                        'trend': latest.trend,
                        'timestamp': latest.timestamp
                    }

        with self.actions_lock:
            recent_actions = list(self.scaling_actions)[-10:]  # Last 10 actions

        with self.cost_lock:
            total_cost = sum(cost_entry['cost'] for cost_entry in self.cost_history if cost_entry['timestamp'] > time.time() - 3600)

        return {
            'cloud_provider': self.cloud_provider.value,
            'auto_scaling_groups': groups_status,
            'current_metrics': latest_metrics,
            'recent_scaling_actions': recent_actions,
            'total_resources': len(self.cloud_resources),
            'active_resources': len([r for r in self.cloud_resources.values() if r.state == 'running']),
            'hourly_cost': total_cost,
            'predictive_scaling_enabled': self.predictive_scaling_enabled,
            'cost_optimization_enabled': self.cost_optimization_enabled,
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }

    def manual_scale(self, group_id: str, target_capacity: int, reason: str = "Manual scaling") -> bool:
        """Manually scale an auto-scaling group"""

        with self.group_lock:
            if group_id not in self.auto_scaling_groups:
                logger.log("ERROR", "ScalableCloudOps", f"Auto-scaling group {group_id} not found")
                return False

            group = self.auto_scaling_groups[group_id]

            # Validate target capacity
            if target_capacity < group.min_size or target_capacity > group.max_size:
                logger.log("ERROR", "ScalableCloudOps", f"Target capacity {target_capacity} out of range [{group.min_size}, {group.max_size}]")
                return False

            # Check cooldown
            if time.time() < group.cooldown_until:
                logger.log("WARNING", "ScalableCloudOps", f"Group {group_id} is in cooldown period")
                return False

        # Execute scaling
        success = self._scale_group_to_capacity(group, target_capacity)

        if success:
            # Record scaling action
            action = ScalingAction(
                action_id=f"manual_{int(time.time())}_{random.randint(1000, 9999)}",
                policy_id="manual",
                direction=ScalingDirection.SCALE_UP if target_capacity > len(group.current_instances) else ScalingDirection.SCALE_DOWN,
                current_instances=len(group.current_instances),
                target_instances=target_capacity,
                reason=reason,
                executed=True,
                success=True,
                execution_time=time.time()
            )

            with self.actions_lock:
                self.scaling_actions.append(action)

            group.last_scaling_action = action
            group.desired_capacity = target_capacity
            group.cooldown_until = time.time() + 60  # 1 minute cooldown for manual scaling

            logger.log("INFO", "ScalableCloudOps", f"Manual scaling of group {group_id} to {target_capacity} instances")

        return success

    def _collect_metrics(self):
        """Collect resource utilization metrics"""

        while self.running:
            try:
                # Collect system metrics
                metrics_data = self._collect_system_metrics()

                with self.metrics_lock:
                    for resource_type, value in metrics_data.items():
                        rt = ResourceType(resource_type)

                        # Calculate utilization percentage
                        max_value = self._get_resource_max(rt)
                        utilization = (value / max_value) * 100 if max_value > 0 else 0

                        # Determine trend
                        trend = self._calculate_trend(rt, utilization)

                        metric = ResourceMetrics(
                            resource_type=rt,
                            current_value=value,
                            max_value=max_value,
                            utilization_percent=utilization,
                            trend=trend
                        )

                        self.resource_metrics[rt].append(metric)

                # Update cost tracking
                self._update_cost_tracking()

            except Exception as e:
                logger.log("ERROR", "ScalableCloudOps", f"Metrics collection error: {str(e)}")

            time.sleep(self.metrics_collection_interval)

    def _evaluate_scaling(self):
        """Evaluate scaling policies and execute scaling actions"""

        while self.running:
            try:
                # Evaluate each auto-scaling group
                with self.group_lock:
                    for group_id, group in self.auto_scaling_groups.items():
                        if time.time() < group.cooldown_until:
                            continue  # Group is in cooldown

                        # Evaluate scaling policies
                        scaling_decision = self._evaluate_group_scaling(group)

                        if scaling_decision['direction'] != ScalingDirection.NO_CHANGE:
                            self._execute_scaling_action(group, scaling_decision)

            except Exception as e:
                logger.log("ERROR", "ScalableCloudOps", f"Scaling evaluation error: {str(e)}")

            time.sleep(self.scaling_evaluation_interval)

    def _analyze_patterns(self):
        """Analyze workload patterns for predictive scaling"""

        while self.running:
            try:
                self._update_workload_patterns()
                self._optimize_scaling_policies()

            except Exception as e:
                logger.log("ERROR", "ScalableCloudOps", f"Pattern analysis error: {str(e)}")

            time.sleep(self.pattern_analysis_interval)

    def _monitor_resources(self):
        """Monitor cloud resources and update their status"""

        while self.running:
            try:
                # Update resource states
                self._update_resource_states()

                # Check for failed resources
                self._handle_failed_resources()

                # Optimize resource allocation
                if self.cost_optimization_enabled:
                    self._optimize_resource_allocation()

            except Exception as e:
                logger.log("ERROR", "ScalableCloudOps", f"Resource monitoring error: {str(e)}")

            time.sleep(60)  # Check every minute

    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system resource metrics"""

        # In a real implementation, this would collect from the actual system/cloud provider
        # For demonstration, we'll simulate realistic metrics

        return {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent,
            'network': random.uniform(10, 90)  # Simulated network usage
        }

    def _get_resource_max(self, resource_type: ResourceType) -> float:
        """Get the maximum value for a resource type"""

        max_values = {
            ResourceType.CPU: 100.0,
            ResourceType.MEMORY: 100.0,
            ResourceType.DISK: 100.0,
            ResourceType.NETWORK: 1000.0,  # Mbps
            ResourceType.GPU: 100.0
        }

        return max_values.get(resource_type, 100.0)

    def _calculate_trend(self, resource_type: ResourceType, current_utilization: float) -> str:
        """Calculate utilization trend"""

        with self.metrics_lock:
            metrics_queue = self.resource_metrics[resource_type]
            if len(metrics_queue) < 5:
                return "stable"

            recent = list(metrics_queue)[-5:]
            values = [m.utilization_percent for m in recent]

            if len(values) >= 2:
                slope = statistics.linear_regression(range(len(values)), values)[0]
                if slope > 1:
                    return "increasing"
                elif slope < -1:
                    return "decreasing"

            return "stable"

    def _evaluate_group_scaling(self, group: AutoScalingGroup) -> Dict[str, Any]:
        """Evaluate scaling decision for an auto-scaling group"""

        current_capacity = len(group.current_instances)
        decision = {
            'direction': ScalingDirection.NO_CHANGE,
            'target_capacity': current_capacity,
            'reason': 'No scaling needed',
            'confidence': 0.0
        }

        # Evaluate each scaling policy
        for policy_id in group.scaling_policies:
            with self.policy_lock:
                if policy_id not in self.scaling_policies:
                    continue

                policy = self.scaling_policies[policy_id]
                if not policy.enabled:
                    continue

            # Get current metrics for this resource type
            with self.metrics_lock:
                metrics_queue = self.resource_metrics[policy.resource_type]
                if not metrics_queue:
                    continue

                current_metric = metrics_queue[-1]

            # Evaluate scaling conditions
            utilization = current_metric.utilization_percent

            if policy.scaling_strategy == ScalingStrategy.REACTIVE:
                # Reactive scaling based on current utilization
                if utilization >= policy.scale_up_threshold:
                    new_capacity = min(current_capacity + 1, policy.max_instances)
                    if new_capacity > current_capacity:
                        decision.update({
                            'direction': ScalingDirection.SCALE_UP,
                            'target_capacity': new_capacity,
                            'reason': f'{policy.resource_type.value} utilization {utilization:.1f}% >= {policy.scale_up_threshold}%',
                            'confidence': 0.8,
                            'policy_id': policy_id
                        })

                elif utilization <= policy.scale_down_threshold and current_capacity > policy.min_instances:
                    new_capacity = max(current_capacity - 1, policy.min_instances)
                    if new_capacity < current_capacity:
                        decision.update({
                            'direction': ScalingDirection.SCALE_DOWN,
                            'target_capacity': new_capacity,
                            'reason': f'{policy.resource_type.value} utilization {utilization:.1f}% <= {policy.scale_down_threshold}%',
                            'confidence': 0.7,
                            'policy_id': policy_id
                        })

            elif policy.scaling_strategy == ScalingStrategy.PREDICTIVE:
                # Predictive scaling based on forecasted utilization
                predicted_utilization = self._predict_utilization(policy.resource_type, policy.predictive_window)

                if predicted_utilization >= policy.scale_up_threshold:
                    new_capacity = min(current_capacity + 1, policy.max_instances)
                    if new_capacity > current_capacity:
                        decision.update({
                            'direction': ScalingDirection.SCALE_UP,
                            'target_capacity': new_capacity,
                            'reason': f'Predicted {policy.resource_type.value} utilization {predicted_utilization:.1f}% >= {policy.scale_up_threshold}%',
                            'confidence': 0.6,
                            'policy_id': policy_id
                        })

        return decision

    def _predict_utilization(self, resource_type: ResourceType, window_seconds: int) -> float:
        """Predict future utilization for a resource type"""

        with self.metrics_lock:
            metrics_queue = self.resource_metrics[resource_type]
            if len(metrics_queue) < 10:
                return 0.0

            # Simple prediction based on recent trend
            recent = list(metrics_queue)[-10:]
            values = [m.utilization_percent for m in recent]

            # Calculate trend
            if len(values) >= 2:
                slope = statistics.linear_regression(range(len(values)), values)[0]
                predicted = values[-1] + (slope * (window_seconds / self.metrics_collection_interval))
                return max(0, min(100, predicted))

            return statistics.mean(values)

    def _execute_scaling_action(self, group: AutoScalingGroup, decision: Dict[str, Any]):
        """Execute a scaling action"""

        # Check scaling rate limits
        with self.actions_lock:
            recent_actions = [a for a in self.scaling_actions if a.timestamp > time.time() - 3600]
            if len(recent_actions) >= self.max_scaling_actions_per_hour:
                logger.log("WARNING", "ScalableCloudOps", "Scaling rate limit exceeded")
                return

        # Execute the scaling
        success = self._scale_group_to_capacity(group, decision['target_capacity'])

        if success:
            # Record the scaling action
            action = ScalingAction(
                action_id=f"auto_{int(time.time())}_{random.randint(1000, 9999)}",
                policy_id=decision.get('policy_id', 'unknown'),
                direction=decision['direction'],
                current_instances=len(group.current_instances),
                target_instances=decision['target_capacity'],
                reason=decision['reason'],
                executed=True,
                success=True,
                execution_time=time.time(),
                metadata={'confidence': decision.get('confidence', 0.0)}
            )

            with self.actions_lock:
                self.scaling_actions.append(action)

            group.last_scaling_action = action
            group.desired_capacity = decision['target_capacity']
            group.cooldown_until = time.time() + 300  # 5 minute cooldown

            logger.log("INFO", "ScalableCloudOps", f"Executed scaling action for group {group.group_id}: {decision['direction'].value} to {decision['target_capacity']} instances")

    def _scale_group_to_capacity(self, group: AutoScalingGroup, target_capacity: int) -> bool:
        """Scale an auto-scaling group to the target capacity"""

        current_capacity = len(group.current_instances)

        if target_capacity == current_capacity:
            return True

        try:
            if target_capacity > current_capacity:
                # Scale up
                instances_to_add = target_capacity - current_capacity
                for i in range(instances_to_add):
                    resource = self._launch_resource(group)
                    if resource:
                        group.current_instances.append(resource)
                        with self.resource_lock:
                            self.cloud_resources[resource.resource_id] = resource

            else:
                # Scale down
                instances_to_remove = current_capacity - target_capacity
                for i in range(instances_to_remove):
                    if group.current_instances:
                        resource = group.current_instances.pop()
                        self._terminate_resource(resource)
                        with self.resource_lock:
                            if resource.resource_id in self.cloud_resources:
                                del self.cloud_resources[resource.resource_id]

            return True

        except Exception as e:
            logger.log("ERROR", "ScalableCloudOps", f"Failed to scale group {group.group_id}: {str(e)}")
            return False

    def _launch_resource(self, group: AutoScalingGroup) -> Optional[CloudResource]:
        """Launch a new cloud resource"""

        # In a real implementation, this would interact with the cloud provider API
        # For demonstration, we'll simulate resource launching

        resource_id = f"{group.resource_type}_{int(time.time())}_{random.randint(1000, 9999)}"

        resource = CloudResource(
            resource_id=resource_id,
            resource_type=group.resource_type,
            provider=self.cloud_provider,
            instance_type=self._get_instance_type_for_group(group),
            region="us-east-1",  # Default region
            availability_zone="us-east-1a",
            state="running",
            launch_time=time.time(),
            cost_per_hour=self._get_cost_for_instance_type(group.resource_type),
            tags={"auto-scaling-group": group.group_id}
        )

        logger.log("INFO", "ScalableCloudOps", f"Launched resource {resource_id} for group {group.group_id}")
        return resource

    def _terminate_resource(self, resource: CloudResource):
        """Terminate a cloud resource"""

        # In a real implementation, this would interact with the cloud provider API
        logger.log("INFO", "ScalableCloudOps", f"Terminated resource {resource.resource_id}")

    def _get_instance_type_for_group(self, group: AutoScalingGroup) -> str:
        """Get appropriate instance type for a group"""

        # Simple mapping based on resource type
        instance_types = {
            'agent': 't3.medium',
            'worker': 'c5.large',
            'gpu': 'p3.2xlarge',
            'memory': 'r5.large'
        }

        return instance_types.get(group.resource_type, 't3.medium')

    def _get_cost_for_instance_type(self, resource_type: str) -> float:
        """Get cost per hour for an instance type"""

        # Simplified cost estimates (in USD per hour)
        costs = {
            'agent': 0.0416,  # t3.medium
            'worker': 0.096,  # c5.large
            'gpu': 3.06,      # p3.2xlarge
            'memory': 0.126   # r5.large
        }

        return costs.get(resource_type, 0.05)

    def _update_cost_tracking(self):
        """Update cost tracking for running resources"""

        with self.resource_lock:
            running_resources = [r for r in self.cloud_resources.values() if r.state == 'running']

        total_hourly_cost = sum(r.cost_per_hour for r in running_resources)

        with self.cost_lock:
            self.cost_history.append({
                'timestamp': time.time(),
                'resources_count': len(running_resources),
                'cost': total_hourly_cost
            })

    def _initialize_default_policies(self):
        """Initialize default scaling policies"""

        # CPU scaling policy
        self.create_scaling_policy({
            'policy_id': 'cpu_reactive',
            'name': 'CPU Reactive Scaling',
            'resource_type': 'cpu',
            'scaling_strategy': 'reactive',
            'scale_up_threshold': 75.0,
            'scale_down_threshold': 25.0,
            'min_instances': 1,
            'max_instances': 20,
            'cooldown_period': 300
        })

        # Memory scaling policy
        self.create_scaling_policy({
            'policy_id': 'memory_reactive',
            'name': 'Memory Reactive Scaling',
            'resource_type': 'memory',
            'scaling_strategy': 'reactive',
            'scale_up_threshold': 80.0,
            'scale_down_threshold': 30.0,
            'min_instances': 1,
            'max_instances': 15,
            'cooldown_period': 300
        })

        # Predictive CPU scaling
        if self.predictive_scaling_enabled:
            self.create_scaling_policy({
                'policy_id': 'cpu_predictive',
                'name': 'CPU Predictive Scaling',
                'resource_type': 'cpu',
                'scaling_strategy': 'predictive',
                'scale_up_threshold': 70.0,
                'scale_down_threshold': 20.0,
                'min_instances': 1,
                'max_instances': 25,
                'cooldown_period': 600,
                'predictive_window': 900
            })

    def _update_workload_patterns(self):
        """Update workload patterns for predictive scaling"""

        # Analyze historical metrics to identify patterns
        with self.metrics_lock:
            for resource_type, metrics_queue in self.resource_metrics.items():
                if len(metrics_queue) < 100:  # Need sufficient data
                    continue

                # Simple pattern detection
                values = [m.utilization_percent for m in metrics_queue]
                mean_utilization = statistics.mean(values)
                std_utilization = statistics.stdev(values) if len(values) > 1 else 0

                # Identify peak periods (simplified)
                peak_threshold = mean_utilization + std_utilization
                peak_times = []

                for i, metric in enumerate(metrics_queue):
                    if metric.utilization_percent > peak_threshold:
                        # Convert timestamp to hour/minute
                        dt = time.localtime(metric.timestamp)
                        peak_times.append((dt.tm_hour, dt.tm_min))

                if peak_times:
                    pattern_id = f"pattern_{resource_type.value}_{int(time.time())}"

                    pattern = WorkloadPattern(
                        pattern_id=pattern_id,
                        resource_type=resource_type,
                        time_window=86400,  # 24 hours
                        pattern_type="daily",
                        peak_times=peak_times[:10],  # Top 10 peak times
                        baseline_utilization=mean_utilization,
                        peak_utilization=max(values),
                        confidence_score=min(0.9, len(peak_times) / 50)  # Confidence based on data points
                    )

                    with self.pattern_lock:
                        self.workload_patterns[pattern_id] = pattern

    def _optimize_scaling_policies(self):
        """Optimize scaling policies based on patterns and performance"""

        # Analyze recent scaling actions to improve policies
        with self.actions_lock:
            recent_actions = list(self.scaling_actions)[-50:]  # Last 50 actions

        if len(recent_actions) < 10:
            return

        # Calculate success rate
        successful_actions = [a for a in recent_actions if a.success]
        success_rate = len(successful_actions) / len(recent_actions)

        # Adjust policy thresholds based on performance
        with self.policy_lock:
            for policy_id, policy in self.scaling_policies.items():
                if not policy.enabled:
                    continue

                # Simple optimization: adjust thresholds based on scaling frequency
                policy_actions = [a for a in recent_actions if a.policy_id == policy_id]

                if len(policy_actions) > 5:
                    scale_up_actions = [a for a in policy_actions if a.direction == ScalingDirection.SCALE_UP]
                    scale_down_actions = [a for a in policy_actions if a.direction == ScalingDirection.SCALE_DOWN]

                    # If too many scale-ups, increase threshold
                    if len(scale_up_actions) > len(scale_down_actions) * 2:
                        policy.scale_up_threshold = min(95.0, policy.scale_up_threshold + 5)
                        logger.log("INFO", "ScalableCloudOps", f"Optimized policy {policy_id}: increased scale-up threshold to {policy.scale_up_threshold}%")

                    # If too many scale-downs, decrease threshold
                    elif len(scale_down_actions) > len(scale_up_actions) * 2:
                        policy.scale_down_threshold = max(5.0, policy.scale_down_threshold - 5)
                        logger.log("INFO", "ScalableCloudOps", f"Optimized policy {policy_id}: decreased scale-down threshold to {policy.scale_down_threshold}%")

    def _update_resource_states(self):
        """Update the state of cloud resources"""

        with self.resource_lock:
            for resource_id, resource in self.cloud_resources.items():
                # In a real implementation, this would query the cloud provider
                # For demonstration, we'll simulate state updates

                # Simulate occasional failures (0.1% chance)
                if random.random() < 0.001 and resource.state == 'running':
                    resource.state = 'stopped'
                    logger.log("WARNING", "ScalableCloudOps", f"Resource {resource_id} stopped unexpectedly")

    def _handle_failed_resources(self):
        """Handle failed or stopped resources"""

        with self.resource_lock:
            failed_resources = [r for r in self.cloud_resources.values() if r.state in ['stopped', 'terminated']]

        for resource in failed_resources:
            # Find the group this resource belongs to
            with self.group_lock:
                for group in self.auto_scaling_groups.values():
                    if resource in group.current_instances:
                        logger.log("WARNING", "ScalableCloudOps", f"Handling failed resource {resource.resource_id} in group {group.group_id}")

                        # Remove failed resource
                        group.current_instances.remove(resource)

                        # Launch replacement if below desired capacity
                        if len(group.current_instances) < group.desired_capacity:
                            new_resource = self._launch_resource(group)
                            if new_resource:
                                group.current_instances.append(new_resource)
                                with self.resource_lock:
                                    self.cloud_resources[new_resource.resource_id] = new_resource

                        break

    def _optimize_resource_allocation(self):
        """Optimize resource allocation for cost efficiency"""

        with self.group_lock:
            for group in self.auto_scaling_groups.values():
                current_capacity = len(group.current_instances)

                # Check if we can scale down for cost optimization
                if current_capacity > group.min_size:
                    # Get current utilization
                    with self.metrics_lock:
                        cpu_metrics = self.resource_metrics[ResourceType.CPU]
                        memory_metrics = self.resource_metrics[ResourceType.MEMORY]

                        if cpu_metrics and memory_metrics:
                            avg_cpu = statistics.mean([m.utilization_percent for m in list(cpu_metrics)[-10:]])
                            avg_memory = statistics.mean([m.utilization_percent for m in list(memory_metrics)[-10:]])

                            # If both CPU and memory are low, consider scaling down
                            if avg_cpu < 30 and avg_memory < 40:
                                # Check if we've been low for a while
                                low_periods = sum(1 for m in list(cpu_metrics)[-20:] if m.utilization_percent < 30)
                                if low_periods > 15:  # 75% of the time
                                    logger.log("INFO", "ScalableCloudOps", f"Cost optimization: low utilization detected for group {group.group_id}, considering scale-down")

# Global scalable cloud ops instance
scalable_cloud_ops = ScalableCloudOps()

# Integration functions
def start_scalable_cloud_ops(provider: CloudProvider = CloudProvider.LOCAL) -> ScalableCloudOps:
    """Start scalable cloud operations"""
    ops = ScalableCloudOps(provider)
    ops.start()
    return ops

def create_scaling_policy(policy_config: Dict[str, Any]) -> str:
    """Create a scaling policy"""
    return scalable_cloud_ops.create_scaling_policy(policy_config)

def create_auto_scaling_group(group_config: Dict[str, Any]) -> str:
    """Create an auto-scaling group"""
    return scalable_cloud_ops.create_auto_scaling_group(group_config)

def manual_scale_group(group_id: str, target_capacity: int, reason: str = "Manual scaling") -> bool:
    """Manually scale an auto-scaling group"""
    return scalable_cloud_ops.manual_scale(group_id, target_capacity, reason)

def get_cloud_scaling_status() -> Dict[str, Any]:
    """Get comprehensive cloud scaling status"""
    return scalable_cloud_ops.get_scaling_status()

def stop_scalable_cloud_ops():
    """Stop scalable cloud operations"""
    scalable_cloud_ops.stop()