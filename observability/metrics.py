"""
Prometheus metrics collection for Brain Swarm
Comprehensive monitoring of system performance, agent activity, and task execution
"""

import time
from typing import Dict, Any, Optional, List

# Try to import prometheus_client, fallback to mock if not available
try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, CollectorRegistry,
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when prometheus_client is not available
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def inc(self, value=1):
            pass
        def set(self, value):
            pass
        def observe(self, value):
            pass

    class Counter(MockMetric): pass
    class Gauge(MockMetric): pass
    class Histogram(MockMetric): pass
    class Summary(MockMetric): pass

    class CollectorRegistry:
        pass

    def generate_latest(registry):
        return "# Prometheus metrics not available\n# Install prometheus_client for full metrics support\n".encode('utf-8')

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"

from ..core.base import logger


class MetricsCollector:
    """Comprehensive metrics collector for Brain Swarm"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()

        # System-level metrics
        self.system_info = Gauge(
            'brain_swarm_system_info',
            'System information',
            ['version', 'environment'],
            registry=self.registry
        )

        # Agent metrics
        self.agent_count = Gauge(
            'brain_swarm_agents_total',
            'Total number of registered agents',
            ['swarm_id'],
            registry=self.registry
        )

        self.agent_load = Gauge(
            'brain_swarm_agent_load',
            'Current load of each agent',
            ['agent_id', 'agent_role', 'swarm_id'],
            registry=self.registry
        )

        self.agent_performance = Gauge(
            'brain_swarm_agent_performance',
            'Agent performance metrics',
            ['agent_id', 'metric_type'],
            registry=self.registry
        )

        # Task metrics
        self.tasks_created = Counter(
            'brain_swarm_tasks_created_total',
            'Total number of tasks created',
            ['task_type', 'priority', 'swarm_id'],
            registry=self.registry
        )

        self.tasks_completed = Counter(
            'brain_swarm_tasks_completed_total',
            'Total number of tasks completed',
            ['task_type', 'status', 'swarm_id'],
            registry=self.registry
        )

        self.task_duration = Histogram(
            'brain_swarm_task_duration_seconds',
            'Task execution duration',
            ['task_type', 'agent_id', 'swarm_id'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
            registry=self.registry
        )

        self.active_tasks = Gauge(
            'brain_swarm_tasks_active',
            'Number of currently active tasks',
            ['swarm_id'],
            registry=self.registry
        )

        # Coordinator metrics
        self.coordinator_operations = Counter(
            'brain_swarm_coordinator_operations_total',
            'Coordinator operations performed',
            ['operation_type', 'swarm_id'],
            registry=self.registry
        )

        self.delegation_latency = Histogram(
            'brain_swarm_delegation_latency_seconds',
            'Time taken to delegate tasks',
            ['swarm_id'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
            registry=self.registry
        )

        # Memory and storage metrics
        self.memory_operations = Counter(
            'brain_swarm_memory_operations_total',
            'Memory operations performed',
            ['operation_type', 'component'],
            registry=self.registry
        )

        self.memory_usage = Gauge(
            'brain_swarm_memory_usage_bytes',
            'Memory usage by component',
            ['component', 'memory_type'],
            registry=self.registry
        )

        # Message queue metrics
        self.messages_sent = Counter(
            'brain_swarm_messages_sent_total',
            'Messages sent between components',
            ['message_type', 'sender_type', 'receiver_type'],
            registry=self.registry
        )

        self.message_processing_time = Histogram(
            'brain_swarm_message_processing_seconds',
            'Time to process messages',
            ['message_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
            registry=self.registry
        )

        # Consensus and debate metrics
        self.consensus_sessions = Counter(
            'brain_swarm_consensus_sessions_total',
            'Consensus sessions conducted',
            ['topic_type', 'participants_count'],
            registry=self.registry
        )

        self.consensus_score = Histogram(
            'brain_swarm_consensus_score',
            'Consensus quality scores',
            ['topic_type'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )

        # Error and failure metrics
        self.errors_total = Counter(
            'brain_swarm_errors_total',
            'Total errors by type and component',
            ['error_type', 'component', 'severity'],
            registry=self.registry
        )

        self.task_failures = Counter(
            'brain_swarm_task_failures_total',
            'Task failures by type and reason',
            ['task_type', 'failure_reason', 'agent_id'],
            registry=self.registry
        )

        # Performance and latency metrics
        self.api_requests = Counter(
            'brain_swarm_api_requests_total',
            'API requests by endpoint and method',
            ['endpoint', 'method', 'status_code'],
            registry=self.registry
        )

        self.api_request_duration = Histogram(
            'brain_swarm_api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )

        # Learning and adaptation metrics
        self.learning_iterations = Counter(
            'brain_swarm_learning_iterations_total',
            'Learning algorithm iterations',
            ['algorithm_type', 'component'],
            registry=self.registry
        )

        self.model_accuracy = Gauge(
            'brain_swarm_model_accuracy',
            'Model accuracy scores',
            ['model_type', 'metric_name'],
            registry=self.registry
        )

        # Federation metrics
        self.federation_operations = Counter(
            'brain_swarm_federation_operations_total',
            'Federation operations performed',
            ['operation_type', 'source_swarm', 'target_swarm'],
            registry=self.registry
        )

        self.inter_swarm_communications = Counter(
            'brain_swarm_inter_swarm_communications_total',
            'Communications between swarms',
            ['communication_type', 'protocol'],
            registry=self.registry
        )

        # Resource utilization metrics
        self.cpu_usage = Gauge(
            'brain_swarm_cpu_usage_percent',
            'CPU usage percentage',
            ['component'],
            registry=self.registry
        )

        self.memory_usage_percent = Gauge(
            'brain_swarm_memory_usage_percent',
            'Memory usage percentage',
            ['component'],
            registry=self.registry
        )

        self.disk_usage = Gauge(
            'brain_swarm_disk_usage_bytes',
            'Disk usage',
            ['component', 'mount_point'],
            registry=self.registry
        )

        # Custom business metrics
        self.business_value_created = Counter(
            'brain_swarm_business_value_created',
            'Business value created by tasks',
            ['value_type', 'task_category'],
            registry=self.registry
        )

        self.user_satisfaction = Gauge(
            'brain_swarm_user_satisfaction_score',
            'User satisfaction scores',
            ['user_type', 'interaction_type'],
            registry=self.registry
        )

    def record_system_info(self, version: str, environment: str):
        """Record system information"""
        self.system_info.labels(version=version, environment=environment).set(1)

    def record_agent_registration(self, agent_id: str, agent_role: str, swarm_id: str):
        """Record agent registration"""
        self.agent_count.labels(swarm_id=swarm_id).inc()
        logger.log("INFO", "MetricsCollector", f"Agent registered: {agent_id}",
                  {"agent_id": agent_id, "agent_role": agent_role, "swarm_id": swarm_id})

    def update_agent_load(self, agent_id: str, agent_role: str, swarm_id: str, load: float):
        """Update agent load metric"""
        self.agent_load.labels(
            agent_id=agent_id,
            agent_role=agent_role,
            swarm_id=swarm_id
        ).set(load)

    def record_task_created(self, task_type: str, priority: int, swarm_id: str):
        """Record task creation"""
        self.tasks_created.labels(
            task_type=task_type,
            priority=str(priority),
            swarm_id=swarm_id
        ).inc()

    def record_task_completed(self, task_type: str, status: str, duration: float,
                            agent_id: str, swarm_id: str):
        """Record task completion"""
        self.tasks_completed.labels(
            task_type=task_type,
            status=status,
            swarm_id=swarm_id
        ).inc()

        self.task_duration.labels(
            task_type=task_type,
            agent_id=agent_id,
            swarm_id=swarm_id
        ).observe(duration)

    def update_active_tasks(self, count: int, swarm_id: str):
        """Update active tasks count"""
        self.active_tasks.labels(swarm_id=swarm_id).set(count)

    def record_coordinator_operation(self, operation_type: str, swarm_id: str):
        """Record coordinator operation"""
        self.coordinator_operations.labels(
            operation_type=operation_type,
            swarm_id=swarm_id
        ).inc()

    def record_delegation(self, duration: float, swarm_id: str):
        """Record task delegation latency"""
        self.delegation_latency.labels(swarm_id=swarm_id).observe(duration)

    def record_memory_operation(self, operation_type: str, component: str, size_bytes: int = 0):
        """Record memory operation"""
        self.memory_operations.labels(
            operation_type=operation_type,
            component=component
        ).inc()

        if size_bytes > 0:
            self.memory_usage.labels(
                component=component,
                memory_type="data_size"
            ).set(size_bytes)

    def record_message(self, message_type: str, sender_type: str, receiver_type: str):
        """Record message sent"""
        self.messages_sent.labels(
            message_type=message_type,
            sender_type=sender_type,
            receiver_type=receiver_type
        ).inc()

    def record_consensus_session(self, topic_type: str, participants_count: int, score: float, duration: float):
        """Record consensus session"""
        self.consensus_sessions.labels(
            topic_type=topic_type,
            participants_count=str(participants_count)
        ).inc()

        self.consensus_score.labels(topic_type=topic_type).observe(score)

    def record_error(self, error_type: str, component: str, severity: str = "medium"):
        """Record error occurrence"""
        self.errors_total.labels(
            error_type=error_type,
            component=component,
            severity=severity
        ).inc()

    def record_task_failure(self, task_type: str, failure_reason: str, agent_id: str):
        """Record task failure"""
        self.task_failures.labels(
            task_type=task_type,
            failure_reason=failure_reason,
            agent_id=agent_id
        ).inc()

    def record_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Record API request"""
        self.api_requests.labels(
            endpoint=endpoint,
            method=method,
            status_code=str(status_code)
        ).inc()

        self.api_request_duration.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

    def record_learning_iteration(self, algorithm_type: str, component: str):
        """Record learning algorithm iteration"""
        self.learning_iterations.labels(
            algorithm_type=algorithm_type,
            component=component
        ).inc()

    def update_model_accuracy(self, model_type: str, metric_name: str, value: float):
        """Update model accuracy metric"""
        self.model_accuracy.labels(
            model_type=model_type,
            metric_name=metric_name
        ).set(value)

    def record_federation_operation(self, operation_type: str, source_swarm: str, target_swarm: str):
        """Record federation operation"""
        self.federation_operations.labels(
            operation_type=operation_type,
            source_swarm=source_swarm,
            target_swarm=target_swarm
        ).inc()

    def update_resource_usage(self, component: str, cpu_percent: float = None,
                            memory_percent: float = None, disk_bytes: int = None):
        """Update resource usage metrics"""
        if cpu_percent is not None:
            self.cpu_usage.labels(component=component).set(cpu_percent)

        if memory_percent is not None:
            self.memory_usage_percent.labels(component=component).set(memory_percent)

        if disk_bytes is not None:
            self.disk_usage.labels(
                component=component,
                mount_point="/"
            ).set(disk_bytes)

    def get_metrics_output(self) -> str:
        """Get Prometheus metrics output"""
        return generate_latest(self.registry).decode('utf-8')

    def get_metrics_json(self) -> Dict[str, Any]:
        """Get metrics in JSON format for dashboards"""
        # This would require parsing the Prometheus output
        # For now, return a summary
        return {
            "timestamp": time.time(),
            "system_status": "operational",
            "metrics_available": True,
            "registry_info": str(self.registry)
        }


# Global metrics collector instance
prometheus_metrics = MetricsCollector()