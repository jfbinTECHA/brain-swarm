# 📚 API Reference

## Overview

BrainSwarmOps provides a comprehensive REST API for incident management, AI processing, and system monitoring.

## Base URL

```
https://api.brainswarm.ai
```

## Authentication

All API endpoints require authentication using JWT tokens.

### Obtaining a Token

#### User Authentication
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "role": "admin"
}
```

#### Agent Authentication
```http
POST /auth/agent-login
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "agent_id": "agent-001"
}
```

### Using Tokens

Include the access token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

## Core Endpoints

### Health Check

#### Get System Health
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "swarm_id": "default-swarm",
  "agent_count": 5,
  "active_tasks": 2,
  "timestamp": 1696545667.123
}
```

### Task Management

#### Create Task
```http
POST /tasks
Content-Type: application/json

{
  "description": "Analyze database performance issue",
  "type": "analysis",
  "priority": 2,
  "resource_requirements": "high"
}
```

Response:
```json
{
  "task_id": "task_1696545667_12345",
  "status": "accepted",
  "strategy": {
    "type": "ai_orchestration",
    "estimated_duration": 300
  }
}
```

#### Get Task Status
```http
GET /tasks/{task_id}
```

Response:
```json
{
  "task_id": "task_1696545667_12345",
  "status": "completed",
  "assigned_agent": "agent-003",
  "created_at": 1696545667.123,
  "completed_at": 1696545967.456,
  "result": {
    "analysis": "Database connection pool exhausted",
    "recommendations": ["Scale connection pool", "Implement circuit breaker"],
    "confidence": 0.92
  }
}
```

### Agent Management

#### List Agents
```http
GET /agents
```

Response:
```json
{
  "agents": [
    {
      "agent_id": "agent-001",
      "current_load": 2,
      "status": "active",
      "type": "analysis"
    },
    {
      "agent_id": "agent-002",
      "current_load": 1,
      "status": "active",
      "type": "execution"
    }
  ],
  "total": 2
}
```

#### Register Agent
```http
POST /agents/register
Content-Type: application/json

{
  "agent_id": "agent-003",
  "agent_type": "specialized",
  "api_key": "secret-key"
}
```

Response:
```json
{
  "status": "registered",
  "agent_id": "agent-003",
  "agent_type": "specialized",
  "coordinator": "default-swarm",
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "role": "agent"
}
```

### Incident Processing

#### Process Alert (AI Triage)
```http
POST /alerts
Content-Type: application/json

{
  "version": "4",
  "groupKey": "alert-group-123",
  "status": "firing",
  "receiver": "webhook",
  "groupLabels": {
    "alertname": "DatabaseConnectionError"
  },
  "commonLabels": {
    "service": "user-db",
    "severity": "critical"
  },
  "commonAnnotations": {
    "summary": "Database connection pool exhausted",
    "description": "Unable to establish database connections"
  },
  "externalURL": "https://alertmanager.brainswarm.ai/alerts",
  "alerts": [
    {
      "labels": {
        "alertname": "DatabaseConnectionError",
        "service": "user-db",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Database connection pool exhausted",
        "description": "Connection pool utilization at 100%"
      },
      "startsAt": "2023-10-05T21:41:07Z"
    }
  ]
}
```

Response:
```json
{
  "task_id": "alert_1696545667_12345",
  "status": "accepted",
  "strategy": {
    "type": "ai_orchestration",
    "alert_id": "alert-group-123"
  }
}
```

### Metrics & Monitoring

#### Get System Metrics
```http
GET /metrics
```

Response:
```json
{
  "agent_metrics": {
    "agent-001": {
      "load": 2,
      "performance": 0.95,
      "status": "active"
    }
  },
  "system_metrics": {
    "total_agents": 5,
    "active_tasks": 3,
    "system_load": 0.4
  },
  "task_metrics": {
    "completed_tasks": 150,
    "failed_tasks": 2,
    "average_completion_time": 245.67
  },
  "timestamp": 1696545667.123
}
```

#### Get Incident Alerts
```http
GET /monitoring/alerts
```

Response:
```json
{
  "active_alerts": [
    {
      "id": "alert-001",
      "name": "DatabaseConnectionError",
      "severity": "critical",
      "status": "firing",
      "description": "Database connection pool exhausted",
      "labels": {
        "service": "user-db",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Connection pool at 100%",
        "runbook": "https://docs.brainswarm.ai/runbooks/database"
      },
      "startsAt": "2023-10-05T21:41:07Z",
      "generatorURL": "https://monitoring.brainswarm.ai/graph?g0.expr=up{service=\"user-db\"}"
    }
  ],
  "alerts_summary": {
    "total_active": 3,
    "critical": 1,
    "warning": 2,
    "info": 0
  },
  "correlation_id": "abc-123-def"
}
```

#### Get Compliance Report
```http
GET /monitoring/compliance?start_time=1696468800&end_time=1696555200
```

Response:
```json
{
  "period": {
    "start": 1696468800,
    "end": 1696555200,
    "duration_hours": 24
  },
  "compliance_score": 98.5,
  "incidents_handled": 12,
  "average_response_time": 245.67,
  "sla_breach_count": 0,
  "recommendations": [
    "Consider implementing additional monitoring for database connections",
    "Review alert thresholds for connection pool utilization"
  ],
  "correlation_id": "def-456-ghi"
}
```

### Scalability Status

#### Get Scalability Metrics
```http
GET /scalability/status
```

Response:
```json
{
  "enabled": true,
  "config": {
    "message_queue_mode": "cluster",
    "async_agents_enabled": true,
    "multi_cluster_enabled": false,
    "auto_scaling_enabled": true
  },
  "components": {
    "async_agents": {
      "pool_metrics": {
        "total_agents": 10,
        "active_agents": 7,
        "avg_utilization": 0.75
      },
      "load_balancer": {
        "routing_efficiency": 0.95,
        "queue_depth": 2
      }
    },
    "message_queue": {
      "mode": "cluster",
      "messages_processed": 15420,
      "messages_failed": 23,
      "success_rate": 0.9985
    },
    "auto_scaling": {
      "current_scale": 3,
      "target_scale": 3,
      "scaling_events": 2
    }
  }
}
```

## Webhook Endpoints

### Alertmanager Webhook
```http
POST /webhook
Content-Type: application/json

{
  "version": "4",
  "groupKey": "alert-group-123",
  "status": "firing",
  "receiver": "brainswarm",
  "groupLabels": {
    "alertname": "ServiceDown"
  },
  "commonLabels": {
    "service": "api-gateway",
    "severity": "critical"
  },
  "commonAnnotations": {
    "summary": "API Gateway is down",
    "description": "API Gateway service is not responding"
  },
  "externalURL": "https://alertmanager.brainswarm.ai/alerts",
  "alerts": [...]
}
```

Response:
```json
{
  "status": "accepted",
  "ticket_system": "github",
  "alerts_count": 1
}
```

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "configured_systems": ["jira", "github", "servicenow"],
  "timestamp": "2023-10-05T21:41:07Z"
}
```

### System Information
```http
GET /
```

Response:
```json
{
  "message": "Brain Swarm API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health",
  "observability": {
    "health": "/health",
    "metrics": "/metrics",
    "alerts": "/monitoring/alerts",
    "compliance": "/monitoring/compliance",
    "traces": "/monitoring/traces",
    "dashboard": "/monitoring/dashboard"
  },
  "scalability": {
    "status": "/scalability/status",
    "enabled_features": ["async_agents", "scalable_message_queue"]
  }
}
```

## Error Responses

### Authentication Error
```json
{
  "detail": "Invalid authentication credentials",
  "type": "authentication_error",
  "status_code": 401
}
```

### Authorization Error
```json
{
  "detail": "Insufficient permissions",
  "type": "authorization_error",
  "status_code": 403
}
```

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "type": "validation_error",
  "status_code": 422
}
```

### Rate Limit Error
```json
{
  "detail": "Rate limit exceeded",
  "type": "rate_limit_error",
  "retry_after": 60,
  "status_code": 429
}
```

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/webhook` | 30 requests | 1 minute |
| `/tasks` | 10 requests | 1 minute |
| `/alerts` | 20 requests | 1 minute |
| `/metrics` | 60 requests | 1 minute |
| Other endpoints | 100 requests | 1 minute |

## SDKs and Libraries

### Python Client
```python
from brainswarm import BrainSwarmClient

client = BrainSwarmClient(
    base_url="https://api.brainswarm.ai",
    api_key="your-api-key"
)

# Create incident
incident = client.create_incident({
    "title": "Database Connection Error",
    "description": "Connection pool exhausted",
    "severity": "critical",
    "service": "user-db"
})

# Get incident status
status = client.get_incident_status(incident["id"])
```

### JavaScript Client
```javascript
import { BrainSwarmAPI } from 'brainswarm-js';

const client = new BrainSwarmAPI({
  baseURL: 'https://api.brainswarm.ai',
  apiKey: 'your-api-key'
});

// Create task
const task = await client.tasks.create({
  description: 'Analyze performance issue',
  priority: 2
});

// Monitor progress
const status = await client.tasks.getStatus(task.id);
```

## Webhooks

### Supported Platforms

#### GitHub Webhooks
- **URL**: `https://webhooks.brainswarm.ai/gh-webhook`
- **Events**: `issues.opened`, `issues.closed`, `issues.assigned`
- **Authentication**: HMAC SHA-256 signature verification

#### Jira Webhooks
- **URL**: `https://webhooks.brainswarm.ai/jira-webhook`
- **Events**: `issue_created`, `issue_updated`, `issue_deleted`
- **Authentication**: Basic authentication or API tokens

#### ServiceNow Webhooks
- **URL**: `https://webhooks.brainswarm.ai/servicenow-webhook`
- **Events**: `incident.inserted`, `incident.updated`, `incident.deleted`
- **Authentication**: OAuth2 or API keys

### Webhook Payload Examples

#### GitHub Issue Created
```json
{
  "action": "opened",
  "issue": {
    "html_url": "https://github.com/org/repo/issues/123",
    "title": "🚨 CRITICAL: API Gateway Down",
    "body": "## Incident Details\n\n**Service**: api-gateway\n**Impact**: All API calls failing\n\n**Error**: Connection timeout\n**Users Affected**: 1000+",
    "labels": [{"name": "critical"}, {"name": "incident"}]
  },
  "repository": {
    "name": "api-gateway",
    "owner": {"login": "my-org"}
  }
}
```

#### Jira Issue Updated
```json
{
  "webhookEvent": "issue_updated",
  "issue": {
    "key": "PROJ-123",
    "fields": {
      "summary": "Database Performance Degradation",
      "description": "Database response times increased by 300%",
      "priority": {"name": "Critical"},
      "status": {"name": "In Progress"}
    }
  }
}
```

## Real-time Updates

### WebSocket Connection
```javascript
const ws = new WebSocket('wss://api.brainswarm.ai/ws/swarm-view');

// Connection established
ws.onopen = () => {
  console.log('Connected to BrainSwarmOps');
};

// Receive real-time updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'incident_update') {
    console.log('Incident update:', data.payload);
  }
};
```

### Server-Sent Events
```javascript
const eventSource = new EventSource('https://api.brainswarm.ai/events');

// Listen for incident events
eventSource.addEventListener('incident', (event) => {
  const incident = JSON.parse(event.data);
  console.log('New incident:', incident);
});
```

## Best Practices

### Error Handling
```python
try:
    response = client.create_task(task_data)
    task_id = response["task_id"]
except HTTPError as e:
    if e.response.status_code == 429:
        # Rate limited, implement backoff
        time.sleep(int(e.response.headers.get('Retry-After', 60)))
    elif e.response.status_code == 422:
        # Validation error
        errors = e.response.json()["detail"]
        # Handle validation errors
    else:
        # Other error
        raise
```

### Pagination
```python
# For endpoints that return lists
page = 1
while True:
    response = client.get_incidents(page=page, limit=50)
    incidents = response["incidents"]
    
    if not incidents:
        break
    
    # Process incidents
    for incident in incidents:
        process_incident(incident)
    
    page += 1
```

### Authentication Token Refresh
```python
class AuthenticatedClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
    
    def _refresh_token(self):
        response = requests.post(f"{self.base_url}/auth/refresh", json={
            "refresh_token": self.refresh_token
        })
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
    
    def request(self, method, endpoint, **kwargs):
        if not self.access_token:
            self._login()
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs["headers"] = headers
        
        response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
        
        if response.status_code == 401:
            # Token expired, refresh and retry
            self._refresh_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
        
        return response
```

This API reference provides comprehensive coverage of all BrainSwarmOps endpoints and integration patterns. For additional examples and use cases, refer to the [examples directory](examples/).