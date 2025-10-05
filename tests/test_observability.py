"""
Tests for Brain Swarm observability components
"""

import pytest
import time
from unittest.mock import Mock, patch

from observability.metrics import prometheus_metrics
from observability.health import health_checker, HealthStatus
from observability.tracing import tracing_manager, get_correlation_id
from observability.governance import governance_monitor
from observability.alerting import alert_manager, AlertSeverity


class TestMetricsCollector:
    """Test Prometheus metrics collection"""

    def test_agent_registration_metric(self):
        """Test agent registration metric recording"""
        prometheus_metrics.record_agent_registration("test_agent", "TestAgent", "test_swarm")

        # Check that metrics are being collected (basic smoke test)
        metrics_output = prometheus_metrics.get_metrics_output()
        assert "brain_swarm_agents_total" in metrics_output
        assert "test_swarm" in metrics_output

    def test_task_metrics(self):
        """Test task-related metrics"""
        prometheus_metrics.record_task_created("analysis", 3, "test_swarm")
        prometheus_metrics.record_task_completed("analysis", "completed", 1.5, "test_agent", "test_swarm")

        metrics_output = prometheus_metrics.get_metrics_output()
        assert "brain_swarm_tasks_created_total" in metrics_output
        assert "brain_swarm_tasks_completed_total" in metrics_output
        assert "brain_swarm_task_duration_seconds" in metrics_output

    def test_api_request_metrics(self):
        """Test API request metrics"""
        prometheus_metrics.record_api_request("/health", "GET", 200, 0.05)

        metrics_output = prometheus_metrics.get_metrics_output()
        assert "brain_swarm_api_requests_total" in metrics_output
        assert "brain_swarm_api_request_duration_seconds" in metrics_output


class TestHealthChecker:
    """Test health check system"""

    def test_register_health_check(self):
        """Test registering a health check"""
        def mock_check():
            return health_checker.HealthCheckResult(
                name="test_check",
                status=HealthStatus.HEALTHY,
                message="Test passed",
                details={"test": True},
                timestamp=time.time(),
                duration_ms=10.0
            )

        health_checker.register_check("test_check", mock_check, interval_seconds=60)

        assert "test_check" in health_checker.checks

    def test_run_health_check(self):
        """Test running a health check"""
        def mock_check():
            return health_checker.HealthCheckResult(
                name="test_check",
                status=HealthStatus.HEALTHY,
                message="Test passed",
                details={"test": True},
                timestamp=time.time(),
                duration_ms=10.0
            )

        health_checker.register_check("test_check", mock_check)

        result = health_checker.run_check("test_check")
        assert result is not None
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test passed"

    def test_overall_health_status(self):
        """Test overall health status calculation"""
        # Register a healthy check
        def healthy_check():
            return health_checker.HealthCheckResult(
                name="healthy_check",
                status=HealthStatus.HEALTHY,
                message="All good",
                details={},
                timestamp=time.time(),
                duration_ms=5.0
            )

        health_checker.register_check("healthy_check", healthy_check)

        overall = health_checker.get_overall_health()
        assert overall["status"] == "healthy"
        assert overall["checks_healthy"] >= 1


class TestTracingManager:
    """Test distributed tracing"""

    def test_start_span(self):
        """Test starting a trace span"""
        span = tracing_manager.start_span("test_operation", tags={"test": True})

        assert span.name == "test_operation"
        assert span.tags["test"] is True
        assert span.span_id is not None
        assert span.trace_id is not None

        # Clean up
        tracing_manager.finish_span(span)

    def test_trace_context_manager(self):
        """Test trace context manager"""
        with tracing_manager.trace_context("test_context", tags={"context": "test"}):
            # Should create and finish span automatically
            pass

        # Check that span was created and finished
        completed_spans = tracing_manager.get_completed_spans()
        assert len(completed_spans) >= 1

        recent_span = completed_spans[-1]
        assert recent_span.name == "test_context"
        assert recent_span.tags["context"] == "test"

    def test_correlation_id(self):
        """Test correlation ID generation and retrieval"""
        correlation_id = get_correlation_id()
        assert correlation_id is not None
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0

        # Should return the same ID within the same context
        correlation_id2 = get_correlation_id()
        assert correlation_id == correlation_id2


class TestGovernanceMonitor:
    """Test governance and compliance monitoring"""

    def test_register_policy(self):
        """Test registering a governance policy"""
        def mock_policy_check(context, threshold=0.8):
            agent_loads = context.get("agent_loads", {})
            overloaded = any(load > threshold for load in agent_loads.values())
            return {
                "status": "violation" if overloaded else "compliant",
                "message": f"Agent load check: {'overloaded' if overloaded else 'normal'}",
                "details": {"threshold": threshold, "agent_loads": agent_loads}
            }

        from observability.governance import PolicyRule, PolicyCategory, ComplianceLevel

        policy = PolicyRule(
            id="test_load_policy",
            name="Test Load Policy",
            description="Test agent load monitoring",
            category=PolicyCategory.PERFORMANCE,
            severity=ComplianceLevel.WARNING,
            check_function=mock_policy_check,
            parameters={"threshold": 0.9}
        )

        governance_monitor.register_policy(policy)
        assert "test_load_policy" in governance_monitor.policies

    def test_evaluate_policy(self):
        """Test policy evaluation"""
        # Use existing policy
        context = {"agent_loads": {"agent1": 0.5, "agent2": 0.7}}
        result = governance_monitor.evaluate_policy("agent_load_limit", context)

        assert result["rule_id"] == "agent_load_limit"
        assert "status" in result
        assert "message" in result

    def test_compliance_report(self):
        """Test compliance report generation"""
        report = governance_monitor.get_compliance_report()

        assert "summary" in report
        assert "category_breakdown" in report
        assert "generated_at" in report
        assert isinstance(report["generated_at"], float)


class TestAlertManager:
    """Test alerting system"""

    def test_register_alert_rule(self):
        """Test registering an alert rule"""
        from observability.alerting import AlertRule

        def mock_condition(context):
            return context.get("cpu_percent", 0) > 80

        rule = AlertRule(
            rule_id="test_cpu_alert",
            name="High CPU Usage",
            description="CPU usage exceeds 80%",
            condition=mock_condition,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=60
        )

        alert_manager.register_rule(rule)
        assert "test_cpu_alert" in alert_manager.rules

    def test_evaluate_rules(self):
        """Test alert rule evaluation"""
        # Create a rule that should trigger
        def high_cpu_condition(context):
            return context.get("cpu_percent", 0) > 50

        from observability.alerting import AlertRule

        rule = AlertRule(
            rule_id="test_high_cpu",
            name="High CPU Alert",
            description="CPU usage is high",
            condition=high_cpu_condition,
            severity=AlertSeverity.WARNING
        )

        alert_manager.register_rule(rule)

        # Evaluate with high CPU
        alert_manager.evaluate_rules({"cpu_percent": 75})

        # Check if alert was created
        active_alerts = alert_manager.get_active_alerts()
        cpu_alerts = [a for a in active_alerts if a.alert_id.startswith("test_high_cpu")]
        assert len(cpu_alerts) >= 1

    def test_dashboard_data(self):
        """Test alert dashboard data"""
        dashboard = alert_manager.get_dashboard_data()

        assert "active_alerts" in dashboard
        assert "severity_breakdown" in dashboard
        assert "component_breakdown" in dashboard
        assert "timeline" in dashboard
        assert "generated_at" in dashboard


class TestObservabilityIntegration:
    """Test integration between observability components"""

    def test_full_observability_flow(self):
        """Test complete observability workflow"""
        # 1. Start a trace
        with tracing_manager.trace_context("integration_test", tags={"test_type": "integration"}):
            # 2. Record some metrics
            prometheus_metrics.record_task_created("integration_test", 1, "test_swarm")

            # 3. Check health
            health_result = health_checker.get_overall_health()

            # 4. Evaluate governance
            governance_result = governance_monitor.evaluate_all_policies({})

            # 5. Check alerts
            alert_dashboard = alert_manager.get_dashboard_data()

        # Verify everything worked
        assert health_result is not None
        assert governance_result is not None
        assert alert_dashboard is not None

        # Check that trace was completed
        completed_spans = tracing_manager.get_completed_spans()
        integration_spans = [s for s in completed_spans if s.name == "integration_test"]
        assert len(integration_spans) >= 1

        # Check that metrics were recorded
        metrics_output = prometheus_metrics.get_metrics_output()
        assert "integration_test" in metrics_output


if __name__ == "__main__":
    pytest.main([__file__])