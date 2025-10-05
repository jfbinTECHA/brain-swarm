# Run a Simulation

This page demonstrates how to run simulations of the Brain Swarm Federation system, including curl commands for triggering incidents, monitoring live Prometheus metrics, and viewing Grafana dashboards.

## Prerequisites

Ensure the Brain Swarm system is running with all components:

```bash
# Start the full stack
docker-compose up -d

# Or run individual services
python -m api.main &
python -m cortex.ingest &
# ... other services
```

## Webhook Integration Testing

Before running simulations, configure webhook endpoints for external integrations:

### GitHub Webhook Testing
```bash
# Test GitHub webhook endpoint
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-GitHub-Event: issues" \
  -d '{
    "action": "opened",
    "issue": {
      "number": 123,
      "title": "Critical Security Vulnerability",
      "body": "Found critical security issue in authentication",
      "labels": [{"name": "security"}, {"name": "critical"}]
    },
    "repository": {"full_name": "myorg/myrepo"}
  }'
```

### Jira Webhook Testing
```bash
# Test Jira webhook endpoint
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "webhookEvent": "jira:issue_created",
    "issue": {
      "key": "PROJ-123",
      "fields": {
        "summary": "Database Connection Failure",
        "description": "Production database is unreachable",
        "priority": {"name": "Highest"},
        "issuetype": {"name": "Incident"}
      }
    }
  }'
```

### ServiceNow Webhook Testing
```bash
# Test ServiceNow webhook endpoint
curl -X POST http://localhost:8000/webhooks/servicenow \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "number": "INC0012345",
    "short_description": "API Gateway Down",
    "description": "Main API gateway is not responding",
    "state": "1",
    "priority": "1",
    "assignment_group": {"display_value": "Platform Team"}
  }'
```

## Starting a Simulation

### 1. Basic Task Simulation

Create a simple task to test the swarm coordination:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "description": "Analyze system performance metrics and provide optimization recommendations",
    "type": "analysis",
    "priority": 2,
    "resource_requirements": "cpu_intensive"
  }'
```

Expected response:
```json
{
  "task_id": "task_1696543210_12345",
  "status": "accepted",
  "strategy": null
}
```

### 2. Incident Simulation (Cortex Alert Processing)

Simulate a critical system alert:

```bash
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "receiver": "brain-swarm-coordinator",
    "status": "firing",
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "HighCPUUsage",
          "service": "web-server",
          "severity": "critical",
          "instance": "web-01:9100"
        },
        "annotations": {
          "description": "CPU usage is above 90% for 5 minutes",
          "summary": "High CPU usage detected"
        },
        "startsAt": "2023-10-05T21:45:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prometheus:9090/graph?g0.expr=cpu_usage_percent%7Binstance%3D%22web-01%3A9100%22%7D+%3E+90&g0.tab=1",
        "fingerprint": "abcd1234"
      }
    ],
    "groupLabels": {
      "alertname": "HighCPUUsage",
      "service": "web-server"
    },
    "commonLabels": {
      "alertname": "HighCPUUsage",
      "service": "web-server",
      "severity": "critical",
      "instance": "web-01:9100"
    },
    "commonAnnotations": {
      "description": "CPU usage is above 90% for 5 minutes",
      "summary": "High CPU usage detected"
    },
    "externalURL": "http://alertmanager:9093",
    "version": "4",
    "groupKey": "{}:{alertname=\"HighCPUUsage\", service=\"web-server\"}",
    "truncatedAlerts": 0
  }'
```

### 3. Load Testing Simulation

Simulate multiple concurrent tasks:

```bash
# Create multiple tasks in parallel
for i in {1..10}; do
  curl -X POST http://localhost:8000/tasks \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    -d "{\"description\": \"Load test task $i: Process data batch $i\", \"type\": \"processing\", \"priority\": 3}" &
done
```

### 4. Federation Stress Test

Test cross-swarm communication:

```bash
# Register agents from different swarms
curl -X POST http://localhost:8000/agents/register \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d "agent_id=agent-federation-01&agent_type=generic&api_key=YOUR_API_KEY"

# Create federation task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "description": "Coordinate data synchronization across federated swarms",
    "type": "federation",
    "priority": 1,
    "resource_requirements": "distributed"
  }'
```

## Live Prometheus Metrics

Monitor system performance in real-time:

### Access Prometheus Metrics

```bash
# Direct metrics endpoint
curl http://localhost:8000/metrics

# Or view in Prometheus UI at http://localhost:9090
```

### Key Metrics to Monitor

```prometheus
# System Health
brain_swarm_api_requests_total{method="POST", endpoint="/tasks"}
brain_swarm_task_completion_time_seconds
brain_swarm_agent_load_ratio

# Federation Metrics
brain_swarm_federation_connections_active
brain_swarm_message_queue_size
brain_swarm_cross_swarm_communication_bytes_total

# Alert Processing
brain_swarm_alert_processing_duration_seconds
brain_swarm_ai_orchestration_decisions_total
```

### Real-time Metrics Dashboard

```bash
# Get current system metrics
curl http://localhost:8000/metrics | grep -E "(brain_swarm|api)"

# Agent status
curl http://localhost:8000/agents

# Task queue status
curl http://localhost:8000/tasks/pending
```

## Grafana Dashboards

View comprehensive dashboards at:

- **Main Dashboard**: http://localhost:3000/d/brain-swarm-main
- **Federation Dashboard**: http://localhost:3000/d/brain-swarm-federation
- **Performance Dashboard**: http://localhost:3000/d/brain-swarm-performance
- **Incident Response Dashboard**: http://localhost:3000/d/brain-swarm-incidents

### Dashboard Snapshots

!!! note "Grafana Snapshots"
    For sharing dashboards without full Grafana access, create snapshots:

    ```bash
    # Create dashboard snapshot via API
    curl -X POST http://localhost:3000/api/dashboards/db/brain-swarm-main/snapshots \
      -H "Authorization: Bearer YOUR_GRAFANA_TOKEN" \
      -d '{"name": "Simulation Run 2023-10-05", "expires": 0}'
    ```

## The Full Triage Loop

### 1. Alert Ingestion
- Cortex receives alerts from Prometheus Alertmanager
- AI agents analyze alert context and severity

```bash
# Simulate alert ingestion
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{"alertname": "ServiceDown", "severity": "critical", "service": "api-gateway"}'
```

### 2. AI-Driven Triage
- Kilo Code AI analyzes the incident
- Determines appropriate response strategy
- Assigns tasks to relevant agents

```bash
# Check AI analysis results
curl http://localhost:8000/tasks/task_1696543210_12345
```

### 3. Automated Response
- Agents execute remediation tasks
- Federation coordinates cross-system actions
- Real-time monitoring tracks progress

```bash
# Monitor task execution
watch -n 2 'curl -s http://localhost:8000/metrics | grep brain_swarm_task'
```

### 4. Learning and Adaptation
- System learns from incident response
- Updates monitoring thresholds
- Improves future triage decisions

```bash
# View learning insights
curl http://localhost:8000/dashboard/learning
```

### 5. Human Oversight (Optional)
- Mission Control dashboard for human monitoring
- Manual intervention capabilities
- Escalation to human operators if needed

```bash
# Access Mission Control
open http://localhost:8000/mission-control
```

## Advanced Simulation Scenarios

### Network Partition Test

```bash
# Simulate network partition
docker network disconnect brain-swarm_default brain-swarm-api-1

# Wait for federation recovery
sleep 30

# Check federation status
curl http://localhost:8000/health
```

### Agent Failure Simulation

```bash
# Simulate agent crash
docker stop brain-swarm-agent-01

# Monitor automatic recovery
curl http://localhost:8000/metrics | grep agent_recovery
```

### Load Spike Simulation

```bash
# Generate load spike
for i in {1..50}; do
  curl -X POST http://localhost:8000/tasks \
    -H "Content-Type: application/json" \
    -d '{"description": "Load spike task '$i'", "priority": 1}' &
done

# Monitor auto-scaling
curl http://localhost:8000/scalability/status
```

## Troubleshooting Simulations

### Common Issues

1. **Tasks not processing**: Check agent registration
   ```bash
   curl http://localhost:8000/agents
   ```

2. **Metrics not updating**: Verify Prometheus configuration
   ```bash
   curl http://localhost:9090/-/ready
   ```

3. **Federation not working**: Check network connectivity
   ```bash
   curl http://localhost:8000/health
   ```

### Debug Commands

```bash
# View system logs
docker-compose logs -f api

# Check message queue status
curl http://localhost:8000/monitoring/dashboard

# Reset simulation state
curl -X POST http://localhost:8000/admin/reset