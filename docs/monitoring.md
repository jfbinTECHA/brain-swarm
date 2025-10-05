---
title: Monitoring & Observability
description: Comprehensive monitoring, metrics, and observability features
---

# Monitoring & Observability

Brain Swarm provides enterprise-grade observability with comprehensive monitoring, metrics collection, distributed tracing, health checks, and alerting capabilities.

## Overview

The observability system includes:

- **Prometheus Metrics**: Real-time performance and system metrics
- **Health Checks**: Automated system health monitoring
- **Distributed Tracing**: Request correlation and performance tracing
- **Alerting**: Rule-based notifications and incident management
- **Governance**: Policy compliance monitoring and reporting
- **Dashboards**: Real-time monitoring interfaces

## Health Checks

### System Health

Get comprehensive system health status:

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "System healthy: all 5 checks passed",
  "checks_total": 5,
  "checks_healthy": 5,
  "checks_degraded": 0,
  "checks_unhealthy": 0,
  "checks_critical": 0,
  "timestamp": 1640995200.123,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "checks": {
    "system_resources": {
      "name": "system_resources",
      "status": "healthy",
      "message": "System resources normal",
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "disk_percent": 23.5
      },
      "timestamp": 1640995200.123,
      "duration_ms": 15.5,
      "tags": ["system", "resources"]
    }
  }
}
```

### Specific Health Checks

Check individual system components:

```http
GET /health/{check_name}
```

Available checks:
- `system_resources`: CPU, memory, and disk usage
- `database_connectivity`: Database connection health
- `external_services`: External API/service connectivity

## Metrics

### Prometheus Metrics

Access Prometheus-formatted metrics:

```http
GET /metrics
```

**Response:** Prometheus metrics in text format:
```
# HELP brain_swarm_agents_total Total number of registered agents
# TYPE brain_swarm_agents_total gauge
brain_swarm_agents_total{swarm_id="default"} 3

# HELP brain_swarm_tasks_active Number of currently active tasks
# TYPE brain_swarm_tasks_active gauge
brain_swarm_tasks_active{swarm_id="default"} 2
```

### Metrics Categories

- **System Metrics**: CPU, memory, disk, network usage
- **Agent Metrics**: Load, performance, success rates
- **Task Metrics**: Creation, completion, failure rates, duration
- **API Metrics**: Request counts, response times, error rates
- **Consensus Metrics**: Debate quality, participant counts
- **Federation Metrics**: Cross-swarm communication

## Alerting

### Active Alerts

Get current alerts and dashboard data:

```http
GET /monitoring/alerts
```

**Response:**
```json
{
  "active_alerts": 2,
  "severity_breakdown": {
    "warning": 1,
    "error": 1
  },
  "component_breakdown": {
    "agent_load": 1,
    "memory_usage": 1
  },
  "timeline": [
    {
      "time": 1640995200.123,
      "severity": "error",
      "title": "High Memory Usage",
      "component": "system_resources",
      "status": "active"
    }
  ],
  "active_alerts_detail": [
    {
      "alert_id": "high_memory_1640995200",
      "title": "High Memory Usage",
      "description": "Memory usage exceeds 90%",
      "severity": "error",
      "status": "active",
      "component": "system_resources",
      "labels": {"category": "system", "resource": "memory"},
      "created_at": 1640995200.123
    }
  ],
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Alert Management

#### Acknowledge Alert

```http
POST /monitoring/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "admin_user"
}
```

#### Resolve Alert

```http
POST /monitoring/alerts/{alert_id}/resolve
Content-Type: application/json

{
  "resolved_by": "admin_user"
}
```

## Compliance & Governance

### Compliance Report

Get policy compliance status:

```http
GET /monitoring/compliance
```

**Response:**
```json
{
  "report_period": {
    "start_time": null,
    "end_time": 1640995200.123
  },
  "summary": {
    "total_events": 150,
    "violations": 3,
    "warnings": 7,
    "compliant": 140,
    "compliance_score": 93.3
  },
  "category_breakdown": {
    "security": {"total": 50, "violations": 1, "warnings": 2},
    "performance": {"total": 60, "violations": 2, "warnings": 3},
    "reliability": {"total": 40, "violations": 0, "warnings": 2}
  },
  "recent_violations": [
    {
      "rule_id": "agent_load_limit",
      "message": "Agent load exceeds maximum threshold",
      "severity": "violation",
      "timestamp": 1640995100.456
    }
  ],
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Policy Categories

- **Security**: Audit logging, access controls, data protection
- **Performance**: Load limits, response times, resource usage
- **Reliability**: Error rates, uptime, failover capabilities
- **Compliance**: Data retention, regulatory requirements
- **Governance**: Process adherence, approval workflows

## Distributed Tracing

### Trace Visualization

Get detailed trace information:

```http
GET /monitoring/traces/{trace_id}
```

**Response:**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "root_spans": [
    {
      "span": {
        "span_id": "span_123",
        "name": "task_execution",
        "service_name": "brain-swarm",
        "start_time": 1640995200000000000,
        "end_time": 1640995201000000000,
        "duration_ns": 1000000000,
        "tags": {"task_type": "analysis"},
        "status_code": "OK"
      },
      "children": [
        {
          "span": {
            "span_id": "span_124",
            "name": "agent_processing",
            "service_name": "brain-swarm",
            "start_time": 1640995200100000000,
            "end_time": 1640995200900000000,
            "duration_ns": 800000000,
            "tags": {"agent_id": "LanguageAgent"}
          },
          "children": []
        }
      ]
    }
  ],
  "total_spans": 2,
  "duration_ns": 1000000000,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Unified Monitoring Dashboard

### Comprehensive Dashboard

Get all monitoring data in one request:

```http
GET /monitoring/dashboard
```

**Response:**
```json
{
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1640995200.123,
  "health": {
    "status": "healthy",
    "checks_total": 5,
    "checks_healthy": 5
  },
  "alerts": {
    "active_alerts": 0,
    "severity_breakdown": {"warning": 0, "error": 0}
  },
  "compliance": {
    "summary": {
      "compliance_score": 96.7,
      "violations": 1,
      "warnings": 3
    }
  },
  "metrics_summary": {
    "total_agents": 3,
    "active_tasks": 2,
    "system_load": 0.45
  },
  "active_traces": 5,
  "system_status": "operational"
}
```

## Configuration

### Alert Rules

Configure custom alert rules in your application:

```python
from observability.alerting import alert_manager, AlertRule, AlertSeverity

# Add custom alert rule
alert_manager.register_rule(AlertRule(
    rule_id="custom_high_latency",
    name="High API Latency",
    description="API response time exceeds 5 seconds",
    condition=lambda context: context.get("avg_response_time", 0) > 5.0,
    severity=AlertSeverity.WARNING,
    cooldown_seconds=300
))
```

### Health Checks

Register custom health checks:

```python
from observability.health import health_checker

def custom_service_check():
    # Check your custom service
    return health_checker.HealthCheckResult(
        name="custom_service",
        status=health_checker.HealthStatus.HEALTHY,
        message="Custom service operational",
        details={"version": "1.2.3", "connections": 150},
        timestamp=time.time(),
        duration_ms=25.0,
        tags=["custom", "service"]
    )

health_checker.register_check("custom_service", custom_service_check)
```

### Governance Policies

Add custom compliance policies:

```python
from observability.governance import governance_monitor, PolicyRule, PolicyCategory, ComplianceLevel

def custom_policy_check(context, threshold=100):
    user_count = context.get("active_users", 0)
    return {
        "status": "violation" if user_count > threshold else "compliant",
        "message": f"Active users: {user_count}",
        "details": {"user_count": user_count, "threshold": threshold}
    }

governance_monitor.register_policy(PolicyRule(
    id="user_limit_policy",
    name="User Limit Policy",
    description="Ensure active user count stays within limits",
    category=PolicyCategory.OPERATIONAL,
    severity=ComplianceLevel.WARNING,
    check_function=custom_policy_check,
    parameters={"threshold": 100}
))
```

## Integration Examples

### Python Client

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
health_data = response.json()

# Get metrics
response = requests.get("http://localhost:8000/metrics")
metrics = response.text

# Check alerts
response = requests.get("http://localhost:8000/monitoring/alerts")
alerts = response.json()
```

### Dashboard Integration

```javascript
// Fetch monitoring dashboard
fetch('/monitoring/dashboard')
  .then(response => response.json())
  .then(data => {
    updateHealthStatus(data.health);
    updateAlerts(data.alerts);
    updateMetrics(data.metrics_summary);
  });
```

## Best Practices

### Monitoring Strategy

1. **Set up automated alerts** for critical system conditions
2. **Monitor key metrics** regularly (CPU, memory, task success rates)
3. **Use correlation IDs** to trace requests across components
4. **Configure health checks** for all critical dependencies
5. **Review compliance reports** regularly for policy violations

### Alert Configuration

- **Critical alerts**: System down, data loss, security breaches
- **Warning alerts**: High resource usage, performance degradation
- **Info alerts**: Configuration changes, version updates

### Performance Monitoring

- **Response times**: Keep API responses under 500ms for good UX
- **Error rates**: Maintain under 1% for production systems
- **Resource usage**: Monitor CPU < 80%, Memory < 85%, Disk < 90%
- **Task success**: Maintain > 95% task completion rate

## Troubleshooting

### Common Issues

**High CPU Usage**
- Check active task count
- Review agent load balancing
- Monitor for infinite loops in agents

**Memory Leaks**
- Check for unclosed database connections
- Monitor object creation rates
- Review garbage collection patterns

**Task Failures**
- Check agent health and connectivity
- Review task input validation
- Monitor external service dependencies

### Debug Tools

- **Trace Explorer**: Use `/monitoring/traces/{trace_id}` to debug slow requests
- **Metrics Dashboard**: Monitor real-time performance with `/metrics`
- **Health Checks**: Get detailed system status with `/health`
- **Compliance Reports**: Identify policy violations with `/monitoring/compliance`