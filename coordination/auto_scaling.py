from typing import Dict, List, Any, Optional, Tuple, Set
from ..core.base import logger, metrics
import time
import statistics
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import math

class ScalingStrategy(Enum):
    REACTIVE = "reactive"  # Scale based on current metrics
    PREDICTIVE = "predictive"  # Scale based on predicted load
    SCHEDULED = "scheduled"  # Scale based on time-based schedules
    HYBRID = "hybrid"  # Combination of reactive and predictive

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"  # Horizontal scaling
    SCALE_IN = "scale_in"   # Horizontal scaling
    NO_ACTION = "no_action"

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    NETWORK = "network"
    STORAGE = "storage"

@dataclass
class ScalingPolicy:
    """Defines when and how to scale resources"""
    policy_id: str
    name: str
    resource_type: ResourceType
    scaling_strategy: ScalingStrategy
    scale_up_threshold: float  # Percentage (e.g., 80.0 for 80%)
    scale_down_threshold: float  # Percentage (e.g., 30.0 for 30%)
    min_instances: int = 1
    max_instances: int = 100
    cooldown_period: int = 300  # Seconds between scaling actions
    evaluation_period: int = 60  # Seconds to evaluate metrics
    predictive_window: int = 600  # Seconds to look ahead for predictive scaling
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class ScalingDecision:
    """Represents a scaling decision"""
    decision_id: str
    policy_id: str
    action: ScalingAction
    resource_type: ResourceType
    current_instances: int
    target_instances: int
    reason: str
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkloadMetrics:
    """Current workload metrics"""
    timestamp: float
    cpu_utilization: float
    memory_utilization: float
    network_utilization: float
    active_tasks: int
    queued_tasks: int
    response_time: float
    error_rate: float
    throughput: float

class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITAL_OCEAN = "digital_ocean"
    LINODE = "linode"
    VULTR = "vultr"
    LOCAL = "local"  # For on-premises or local development

@dataclass
class CloudResource:
    """Represents a cloud resource instance"""
    resource_id: str
    provider: CloudProvider
    instance_type: str
    region: str
    zone: str
    state: str  # pending, running, stopping, stopped, terminated
    launch_time: float
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    cost_per_hour: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)

class AutoScaler:
    """Intelligent auto-scaling system for cloud operations"""

    def __init__(self, distributed_coordinator=None):
        self.distributed_coordinator = distributed_coordinator

        # Scaling policies
        self.policies: Dict[str, ScalingPolicy] = {}
        self._initialize_default_policies()

        # Scaling state
        self.scaling_decisions: List[ScalingDecision] = []
        self.last_scaling_actions: Dict[str, float] = {}  # policy_id -> timestamp
        self.current_instances: Dict[str, int] = {}  # resource_type -> count

        # Metrics history for analysis
        self.metrics_history: deque = deque(maxlen=1000)
        self.workload_patterns: Dict[str, List[float]] = {}

        # Cloud resources
        self.cloud_resources: Dict[str, CloudResource] = {}
        self.resource_providers: Dict[CloudProvider, Any] = {}

        # Scaling parameters
        self.scaling_cooldown = 300  # 5 minutes between scaling actions
        self.max_scale_up_instances = 10  # Maximum instances to add at once
        self.max_scale_down_instances = 5  # Maximum instances to remove at once
        self.scale_up_factor = 1.5  # Scale up by 50% of current capacity
        self.scale_down_factor = 0.8  # Scale down to 80% of current capacity

        # Cost optimization
        self.cost_optimization_enabled = True
        self.target_utilization = 0.7  # Target 70% utilization
        self.spot_instance_preference = 0.3  # Use spot instances 30% of the time

    def _initialize_default_policies(self):
        """Initialize default scaling policies"""

        # CPU-based scaling
        self.add_policy(ScalingPolicy(
            policy_id="cpu_reactive_scaling",
            name="CPU Reactive Scaling",
            resource_type=ResourceType.CPU,
            scaling_strategy=ScalingStrategy.REACTIVE,
            scale_up_threshold=75.0,
            scale_down_threshold=30.0,
            min_instances=1,
            max_instances=50,
            cooldown_period=300,
            evaluation_period=60
        ))

        # Memory-based scaling
        self.add_policy(ScalingPolicy(
            policy_id="memory_reactive_scaling",
            name="Memory Reactive Scaling",
            resource_type=ResourceType.MEMORY,
            scaling_strategy=ScalingStrategy.REACTIVE,
            scale_up_threshold=80.0,
            scale_down_threshold=40.0,
            min_instances=1,
            max_instances=30,
            cooldown_period=300,
            evaluation_period=60
        ))

        # Task queue-based scaling
        self.add_policy(ScalingPolicy(
            policy_id="task_queue_scaling",
            name="Task Queue Scaling",
            resource_type=ResourceType.CPU,
            scaling_strategy=ScalingStrategy.REACTIVE,
            scale_up_threshold=50.0,  # 50 queued tasks
            scale_down_threshold=5.0,  # 5 or fewer queued tasks
            min_instances=1,
            max_instances=100,
            cooldown_period=180,
            evaluation_period=30
        ))

        # Predictive scaling based on historical patterns
        self.add_policy(ScalingPolicy(
            policy_id="predictive_workload_scaling",
            name="Predictive Workload Scaling",
            resource_type=ResourceType.CPU,
            scaling_strategy=ScalingStrategy.PREDICTIVE,
            scale_up_threshold=60.0,
            scale_down_threshold=20.0,
            min_instances=1,
            max_instances=75,
            cooldown_period=600,
            evaluation_period=300,
            predictive_window=1800  # 30 minutes ahead
        ))

        # Network-based scaling for high-throughput scenarios
        self.add_policy(ScalingPolicy(
            policy_id="network_scaling",
            name="Network Throughput Scaling",
            resource_type=ResourceType.NETWORK,
            scaling_strategy=ScalingStrategy.REACTIVE,
            scale_up_threshold=70.0,
            scale_down_threshold=25.0,
            min_instances=1,
            max_instances=40,
            cooldown_period=240,
            evaluation_period=45
        ))

    def add_policy(self, policy: ScalingPolicy) -> bool:
        """Add a scaling policy"""
        if policy.policy_id in self.policies:
            logger.log("WARNING", "AutoScaler", f"Policy {policy.policy_id} already exists, updating")
            return False

        self.policies[policy.policy_id] = policy
        logger.log("INFO", "AutoScaler", f"Added scaling policy: {policy.name}")
        return True

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a scaling policy"""
        if policy_id not in self.policies:
            return False

        del self.policies[policy_id]
        logger.log("INFO", "AutoScaler", f"Removed scaling policy: {policy_id}")
        return True

    def record_metrics(self, metrics: WorkloadMetrics):
        """Record current workload metrics for scaling decisions"""
        self.metrics_history.append(metrics)

        # Update workload patterns for predictive scaling
        self._update_workload_patterns(metrics)

    def evaluate_scaling(self) -> List[ScalingDecision]:
        """Evaluate all policies and return scaling decisions"""
        decisions = []
        current_time = time.time()

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            # Check cooldown period
            last_action = self.last_scaling_actions.get(policy.policy_id, 0)
            if current_time - last_action < policy.cooldown_period:
                continue

            # Evaluate policy
            decision = self._evaluate_policy(policy)
            if decision and decision.action != ScalingAction.NO_ACTION:
                decisions.append(decision)
                self.last_scaling_actions[policy.policy_id] = current_time

        # Prioritize and deduplicate decisions
        decisions = self._prioritize_decisions(decisions)
        self.scaling_decisions.extend(decisions)

        return decisions

    def _evaluate_policy(self, policy: ScalingPolicy) -> Optional[ScalingDecision]:
        """Evaluate a single scaling policy"""
        if len(self.metrics_history) < 2:
            return None

        current_metrics = self.metrics_history[-1]
        recent_metrics = list(self.metrics_history)[-policy.evaluation_period//10:]  # Last N metrics

        if policy.scaling_strategy == ScalingStrategy.REACTIVE:
            return self._evaluate_reactive_policy(policy, current_metrics, recent_metrics)
        elif policy.scaling_strategy == ScalingStrategy.PREDICTIVE:
            return self._evaluate_predictive_policy(policy, current_metrics, recent_metrics)
        elif policy.scaling_strategy == ScalingStrategy.SCHEDULED:
            return self._evaluate_scheduled_policy(policy, current_metrics)
        else:  # HYBRID
            reactive_decision = self._evaluate_reactive_policy(policy, current_metrics, recent_metrics)
            predictive_decision = self._evaluate_predictive_policy(policy, current_metrics, recent_metrics)

            # Combine decisions intelligently
            return self._combine_decisions(reactive_decision, predictive_decision)

    def _evaluate_reactive_policy(self, policy: ScalingPolicy, current: WorkloadMetrics,
                                recent: List[WorkloadMetrics]) -> Optional[ScalingDecision]:
        """Evaluate reactive scaling policy"""

        # Get current utilization based on resource type
        current_utilization = self._get_utilization_for_policy(policy, current, recent)

        # Calculate average utilization over evaluation period
        if recent:
            avg_utilization = sum(self._get_utilization_for_policy(policy, m, []) for m in recent) / len(recent)
        else:
            avg_utilization = current_utilization

        current_instances = self.current_instances.get(policy.resource_type.value, policy.min_instances)

        # Scale up decision
        if avg_utilization >= policy.scale_up_threshold:
            scale_up_instances = min(
                self.max_scale_up_instances,
                max(1, int(current_instances * (self.scale_up_factor - 1)))
            )
            target_instances = min(current_instances + scale_up_instances, policy.max_instances)

            if target_instances > current_instances:
                return ScalingDecision(
                    decision_id=f"decision_{int(time.time())}_{policy.policy_id}",
                    policy_id=policy.policy_id,
                    action=ScalingAction.SCALE_OUT if policy.resource_type == ResourceType.CPU else ScalingAction.SCALE_UP,
                    resource_type=policy.resource_type,
                    current_instances=current_instances,
                    target_instances=target_instances,
                    reason=f"High {policy.resource_type.value} utilization: {avg_utilization:.1f}% (threshold: {policy.scale_up_threshold}%)",
                    confidence=min(0.9, (avg_utilization - policy.scale_up_threshold) / 20.0),
                    timestamp=time.time()
                )

        # Scale down decision
        elif avg_utilization <= policy.scale_down_threshold and current_instances > policy.min_instances:
            scale_down_instances = min(
                self.max_scale_down_instances,
                max(1, int(current_instances * (1 - self.scale_down_factor)))
            )
            target_instances = max(current_instances - scale_down_instances, policy.min_instances)

            if target_instances < current_instances:
                return ScalingDecision(
                    decision_id=f"decision_{int(time.time())}_{policy.policy_id}",
                    policy_id=policy.policy_id,
                    action=ScalingAction.SCALE_IN if policy.resource_type == ResourceType.CPU else ScalingAction.SCALE_DOWN,
                    resource_type=policy.resource_type,
                    current_instances=current_instances,
                    target_instances=target_instances,
                    reason=f"Low {policy.resource_type.value} utilization: {avg_utilization:.1f}% (threshold: {policy.scale_down_threshold}%)",
                    confidence=min(0.8, (policy.scale_down_threshold - avg_utilization) / 20.0),
                    timestamp=time.time()
                )

        return ScalingDecision(
            decision_id=f"decision_{int(time.time())}_{policy.policy_id}",
            policy_id=policy.policy_id,
            action=ScalingAction.NO_ACTION,
            resource_type=policy.resource_type,
            current_instances=current_instances,
            target_instances=current_instances,
            reason=f"Utilization within normal range: {avg_utilization:.1f}%",
            confidence=0.5,
            timestamp=time.time()
        )

    def _evaluate_predictive_policy(self, policy: ScalingPolicy, current: WorkloadMetrics,
                                  recent: List[WorkloadMetrics]) -> Optional[ScalingDecision]:
        """Evaluate predictive scaling policy based on workload patterns"""

        # Predict future utilization
        predicted_utilization = self._predict_future_utilization(policy.resource_type, policy.predictive_window)

        if predicted_utilization is None:
            return None

        current_instances = self.current_instances.get(policy.resource_type.value, policy.min_instances)

        # Scale up if predicted utilization is high
        if predicted_utilization >= policy.scale_up_threshold:
            scale_up_instances = min(
                self.max_scale_up_instances,
                max(1, int(current_instances * (self.scale_up_factor - 1)))
            )
            target_instances = min(current_instances + scale_up_instances, policy.max_instances)

            if target_instances > current_instances:
                return ScalingDecision(
                    decision_id=f"predictive_{int(time.time())}_{policy.policy_id}",
                    policy_id=policy.policy_id,
                    action=ScalingAction.SCALE_OUT if policy.resource_type == ResourceType.CPU else ScalingAction.SCALE_UP,
                    resource_type=policy.resource_type,
                    current_instances=current_instances,
                    target_instances=target_instances,
                    reason=f"Predicted high {policy.resource_type.value} utilization: {predicted_utilization:.1f}% in {policy.predictive_window}s",
                    confidence=0.7,  # Predictive scaling has moderate confidence
                    timestamp=time.time(),
                    metadata={"prediction_window": policy.predictive_window, "predicted_value": predicted_utilization}
                )

        return None

    def _evaluate_scheduled_policy(self, policy: ScalingPolicy, current: WorkloadMetrics) -> Optional[ScalingDecision]:
        """Evaluate scheduled scaling policy (placeholder for time-based scaling)"""
        # This would check against predefined schedules
        # For now, return no action
        return None

    def _combine_decisions(self, reactive: Optional[ScalingDecision],
                          predictive: Optional[ScalingDecision]) -> Optional[ScalingDecision]:
        """Combine reactive and predictive scaling decisions"""

        if not reactive and not predictive:
            return None
        if reactive and not predictive:
            return reactive
        if predictive and not reactive:
            return predictive

        # Both decisions exist - combine them
        if reactive.action == predictive.action:
            # Same action - take the one with higher confidence
            return reactive if reactive.confidence >= predictive.confidence else predictive
        else:
            # Conflicting actions - prefer reactive for immediate issues, predictive for planning
            if reactive.action in [ScalingAction.SCALE_UP, ScalingAction.SCALE_OUT]:
                return reactive  # Prioritize scaling up for safety
            else:
                return predictive  # Allow predictive scale down

    def _get_utilization_for_policy(self, policy: ScalingPolicy, metrics: WorkloadMetrics,
                                  recent_metrics: List[WorkloadMetrics]) -> float:
        """Get utilization value for a specific policy"""

        if policy.resource_type == ResourceType.CPU:
            return metrics.cpu_utilization
        elif policy.resource_type == ResourceType.MEMORY:
            return metrics.memory_utilization
        elif policy.resource_type == ResourceType.NETWORK:
            return metrics.network_utilization
        elif policy.resource_type == ResourceType.STORAGE:
            # Storage utilization would need to be tracked separately
            return 50.0  # Placeholder
        else:
            # For task-based policies, use queued tasks as utilization
            if hasattr(metrics, 'queued_tasks'):
                return min(100.0, metrics.queued_tasks * 2.0)  # 50 queued tasks = 100% utilization
            return metrics.cpu_utilization  # Fallback

    def _predict_future_utilization(self, resource_type: ResourceType, window_seconds: int) -> Optional[float]:
        """Predict future utilization using time series analysis"""

        if len(self.metrics_history) < 10:
            return None

        # Simple linear regression for prediction
        recent_metrics = list(self.metrics_history)[-20:]  # Last 20 data points

        # Extract utilization values
        values = []
        for metrics in recent_metrics:
            if resource_type == ResourceType.CPU:
                values.append(metrics.cpu_utilization)
            elif resource_type == ResourceType.MEMORY:
                values.append(metrics.memory_utilization)
            elif resource_type == ResourceType.NETWORK:
                values.append(metrics.network_utilization)
            else:
                values.append(metrics.cpu_utilization)

        if len(values) < 5:
            return None

        # Simple trend analysis
        try:
            # Calculate slope of recent trend
            n = len(values)
            x = list(range(n))
            slope = self._calculate_slope(x, values)

            # Predict future value
            future_steps = window_seconds // 10  # Assuming 10-second intervals
            predicted_value = values[-1] + slope * future_steps

            # Bound prediction
            return max(0.0, min(100.0, predicted_value))

        except Exception:
            return None

    def _calculate_slope(self, x: List[float], y: List[float]) -> float:
        """Calculate slope using linear regression"""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _update_workload_patterns(self, metrics: WorkloadMetrics):
        """Update workload patterns for predictive scaling"""

        # Group metrics by hour of day for pattern recognition
        hour = time.strftime("%H", time.localtime(metrics.timestamp))

        if hour not in self.workload_patterns:
            self.workload_patterns[hour] = []

        self.workload_patterns[hour].append(metrics.cpu_utilization)

        # Keep only recent patterns (last 30 days worth)
        max_patterns = 30 * 24  # 30 days * 24 hours
        for hour_patterns in self.workload_patterns.values():
            if len(hour_patterns) > max_patterns:
                hour_patterns[:] = hour_patterns[-max_patterns:]

    def _prioritize_decisions(self, decisions: List[ScalingDecision]) -> List[ScalingDecision]:
        """Prioritize and deduplicate scaling decisions"""

        if not decisions:
            return []

        # Remove duplicate decisions for same resource type
        seen_resources = set()
        unique_decisions = []

        for decision in decisions:
            resource_key = decision.resource_type.value
            if resource_key not in seen_resources:
                seen_resources.add(resource_key)
                unique_decisions.append(decision)

        # Sort by priority: scale up > scale out > scale down > scale in
        priority_order = {
            ScalingAction.SCALE_UP: 4,
            ScalingAction.SCALE_OUT: 3,
            ScalingAction.SCALE_DOWN: 2,
            ScalingAction.SCALE_IN: 1,
            ScalingAction.NO_ACTION: 0
        }

        unique_decisions.sort(key=lambda d: (
            priority_order.get(d.action, 0),
            d.confidence
        ), reverse=True)

        return unique_decisions

    def execute_scaling_decisions(self, decisions: List[ScalingDecision]) -> List[Dict[str, Any]]:
        """Execute scaling decisions by provisioning/deprovisioning resources"""
        results = []

        for decision in decisions:
            try:
                if decision.action in [ScalingAction.SCALE_UP, ScalingAction.SCALE_OUT]:
                    result = self._scale_up(decision)
                elif decision.action in [ScalingAction.SCALE_DOWN, ScalingAction.SCALE_IN]:
                    result = self._scale_down(decision)
                else:
                    continue

                results.append(result)

                # Update current instance count
                self.current_instances[decision.resource_type.value] = decision.target_instances

                logger.log("INFO", "AutoScaler", f"Executed scaling decision: {decision.action.value} "
                        f"{decision.resource_type.value} from {decision.current_instances} to {decision.target_instances}")

            except Exception as e:
                logger.log("ERROR", "AutoScaler", f"Failed to execute scaling decision {decision.decision_id}: {str(e)}")
                results.append({
                    "decision_id": decision.decision_id,
                    "success": False,
                    "error": str(e)
                })

        return results

    def _scale_up(self, decision: ScalingDecision) -> Dict[str, Any]:
        """Scale up by provisioning new resources"""
        instances_to_add = decision.target_instances - decision.current_instances

        # In a real implementation, this would call cloud provider APIs
        # For now, simulate the scaling

        new_resources = []
        for i in range(instances_to_add):
            resource_id = f"{decision.resource_type.value}_{int(time.time())}_{i}"

            # Simulate cloud resource creation
            resource = CloudResource(
                resource_id=resource_id,
                provider=CloudProvider.AWS,  # Default to AWS
                instance_type="t3.medium",  # Default instance type
                region="us-east-1",
                zone="us-east-1a",
                state="pending",
                launch_time=time.time(),
                cost_per_hour=0.0416  # t3.medium hourly cost
            )

            self.cloud_resources[resource_id] = resource
            new_resources.append(resource)

        return {
            "decision_id": decision.decision_id,
            "success": True,
            "action": "scale_up",
            "instances_added": instances_to_add,
            "new_resources": [r.resource_id for r in new_resources]
        }

    def _scale_down(self, decision: ScalingDecision) -> Dict[str, Any]:
        """Scale down by deprovisioning resources"""
        instances_to_remove = decision.current_instances - decision.target_instances

        # Find resources to remove (prefer oldest first)
        removable_resources = [
            r for r in self.cloud_resources.values()
            if r.state == "running"
        ]

        removable_resources.sort(key=lambda r: r.launch_time)  # Oldest first

        resources_to_remove = removable_resources[:instances_to_remove]

        for resource in resources_to_remove:
            resource.state = "stopping"
            # In real implementation, call cloud provider API to terminate

        return {
            "decision_id": decision.decision_id,
            "success": True,
            "action": "scale_down",
            "instances_removed": len(resources_to_remove),
            "removed_resources": [r.resource_id for r in resources_to_remove]
        }

    def get_scaling_status(self) -> Dict[str, Any]:
        """Get comprehensive scaling status"""
        active_resources = {k: v for k, v in self.cloud_resources.items() if v.state == "running"}
        pending_resources = {k: v for k, v in self.cloud_resources.items() if v.state == "pending"}

        total_cost_per_hour = sum(r.cost_per_hour for r in active_resources.values())

        recent_decisions = self.scaling_decisions[-10:] if self.scaling_decisions else []

        return {
            "policies": {
                policy_id: {
                    "name": policy.name,
                    "enabled": policy.enabled,
                    "resource_type": policy.resource_type.value,
                    "strategy": policy.scaling_strategy.value,
                    "current_instances": self.current_instances.get(policy.resource_type.value, policy.min_instances),
                    "last_action": self.last_scaling_actions.get(policy_id, 0)
                }
                for policy_id, policy in self.policies.items()
            },
            "resources": {
                "active": len(active_resources),
                "pending": len(pending_resources),
                "total": len(self.cloud_resources),
                "cost_per_hour": total_cost_per_hour
            },
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "policy_id": d.policy_id,
                    "action": d.action.value,
                    "resource_type": d.resource_type.value,
                    "instances_change": d.target_instances - d.current_instances,
                    "reason": d.reason,
                    "confidence": d.confidence,
                    "timestamp": d.timestamp
                }
                for d in recent_decisions
            ],
            "metrics_history_size": len(self.metrics_history),
            "workload_patterns": {hour: len(patterns) for hour, patterns in self.workload_patterns.items()},
            "timestamp": time.time()
        }

    def optimize_costs(self) -> List[Dict[str, Any]]:
        """Optimize costs by recommending better instance types or scaling strategies"""
        optimizations = []

        # Analyze current resource utilization vs cost
        for resource in self.cloud_resources.values():
            if resource.state == "running":
                # In a real implementation, this would analyze actual utilization
                # and recommend cost optimizations like:
                # - Switch to spot instances
                # - Use smaller instance types
                # - Use reserved instances
                # - Scale down during low-usage periods

                optimizations.append({
                    "resource_id": resource.resource_id,
                    "recommendation": "Consider using spot instances for cost savings",
                    "potential_savings": resource.cost_per_hour * 0.7,  # 30% savings estimate
                    "confidence": 0.8
                })

        return optimizations

# Global auto-scaler instance
auto_scaler = AutoScaler()

# Integration functions
def initialize_auto_scaling(distributed_coordinator=None) -> AutoScaler:
    """Initialize the auto-scaling system"""
    global auto_scaler
    auto_scaler = AutoScaler(distributed_coordinator)
    return auto_scaler

def record_workload_metrics(metrics: Dict[str, Any]):
    """Record workload metrics for scaling decisions"""
    workload_metrics = WorkloadMetrics(
        timestamp=time.time(),
        cpu_utilization=metrics.get('cpu_utilization', 0.0),
        memory_utilization=metrics.get('memory_utilization', 0.0),
        network_utilization=metrics.get('network_utilization', 0.0),
        active_tasks=metrics.get('active_tasks', 0),
        queued_tasks=metrics.get('queued_tasks', 0),
        response_time=metrics.get('response_time', 0.0),
        error_rate=metrics.get('error_rate', 0.0),
        throughput=metrics.get('throughput', 0.0)
    )

    auto_scaler.record_metrics(workload_metrics)

def evaluate_auto_scaling() -> List[ScalingDecision]:
    """Evaluate all scaling policies and return decisions"""
    return auto_scaler.evaluate_scaling()

def execute_scaling_decisions(decisions: List[ScalingDecision]) -> List[Dict[str, Any]]:
    """Execute scaling decisions"""
    return auto_scaler.execute_scaling_decisions(decisions)

def get_scaling_status() -> Dict[str, Any]:
    """Get current scaling status"""
    return auto_scaler.get_scaling_status()

def get_cost_optimizations() -> List[Dict[str, Any]]:
    """Get cost optimization recommendations"""
    return auto_scaler.optimize_costs()