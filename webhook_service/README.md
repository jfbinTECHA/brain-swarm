# Webhook Service

The Brain Swarm Webhook Service provides dedicated endpoints for processing webhooks from external systems like GitHub, Jira, ServiceNow, and Prometheus Alertmanager.

## Features

- **Multi-Source Support**: Handles webhooks from GitHub, Jira, ServiceNow, and Prometheus
- **Signature Validation**: Validates webhook signatures for security
- **Incident Processing**: Converts webhooks to Brain Swarm incidents
- **Message Queue Integration**: Publishes processed incidents to the message queue
- **Observability**: Full metrics, tracing, and health checks
- **Standalone Service**: Can run as independent microservice

## Supported Webhook Sources

### GitHub
- **Issues**: Critical issues with security/critical labels
- **Pull Requests**: PRs requiring review
- **Workflow Runs**: CI/CD pipeline failures

### Jira
- **Issue Creation**: High-priority issues and bugs
- **Issue Updates**: Status changes to blocked/critical

### ServiceNow
- **Incidents**: New and active incidents based on priority

### Prometheus
- **Alerts**: Alertmanager webhook alerts

## Configuration

### Environment Variables

```bash
# Webhook secrets for signature validation
GITHUB_WEBHOOK_SECRET=your_github_secret
JIRA_WEBHOOK_SECRET=your_jira_secret
SERVICENOW_WEBHOOK_SECRET=your_servicenow_secret

# Service configuration
WEBHOOK_SERVICE_PORT=8080
BRAIN_SWARM_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
```

### Webhook URLs

Configure these URLs in your external systems:

```
GitHub:     https://your-domain.com/webhooks/github
Jira:       https://your-domain.com/webhooks/jira
ServiceNow: https://your-domain.com/webhooks/servicenow
Prometheus: https://your-domain.com/webhooks/prometheus
```

## API Endpoints

### Webhook Endpoints

```http
POST /webhooks/github
POST /webhooks/jira
POST /webhooks/servicenow
POST /webhooks/prometheus
POST /webhooks/{source}  # Generic endpoint
```

### Service Endpoints

```http
GET  /health          # Health check
GET  /metrics         # Prometheus metrics
GET  /stats           # Webhook processing stats
GET  /docs            # API documentation
```

## Usage Examples

### GitHub Webhook Setup

1. **Create webhook in GitHub repository**:
   - Go to Settings → Webhooks → Add webhook
   - Payload URL: `https://your-domain.com/webhooks/github`
   - Content type: `application/json`
   - Secret: Your webhook secret
   - Events: Select "Issues", "Pull requests", "Workflow runs"

2. **Configure secret in environment**:
   ```bash
   export GITHUB_WEBHOOK_SECRET=your_secret_here
   ```

### Jira Webhook Setup

1. **Create webhook in Jira**:
   - Go to System → WebHooks
   - URL: `https://your-domain.com/webhooks/jira`
   - Events: Issue created, Issue updated

2. **Configure authentication** if needed

### ServiceNow Webhook Setup

1. **Create business rule in ServiceNow**:
   - Table: Incident
   - When: After insert/update
   - Action: REST call to webhook URL

### Prometheus Alertmanager

1. **Configure Alertmanager**:
   ```yaml
   receivers:
   - name: 'brain-swarm'
     webhook_configs:
     - url: 'https://your-domain.com/webhooks/prometheus'
   ```

## Running the Service

### Standalone Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run the webhook service
python -m webhook_service.app
```

### Docker

```bash
docker build -t brain-swarm-webhook .
docker run -p 8080:8080 \
  -e GITHUB_WEBHOOK_SECRET=your_secret \
  brain-swarm-webhook
```

### Kubernetes (via Helm)

The webhook service is included in the main Brain Swarm Helm chart:

```bash
helm install brain-swarm ./helm/brain-swarm \
  --set ticketBridge.enabled=true
```

## Incident Processing Logic

### GitHub Issues
- **Critical**: Issues with `security`, `critical`, or `bug` labels
- **High**: Issues with `high` priority labels
- **Medium**: Issues with `medium` priority labels

### Jira Issues
- **Critical**: Priority = "Highest"
- **High**: Priority = "High"
- **Medium**: Priority = "Medium"

### ServiceNow Incidents
- **Critical**: Priority = 1
- **High**: Priority = 2
- **Medium**: Priority = 3

## Message Queue Integration

Processed incidents are published to the message queue with the topic `webhook.incidents`:

```json
{
  "incident": {
    "title": "GitHub Issue: Critical Bug",
    "description": "Issue description...",
    "severity": "critical",
    "source": "github",
    "external_id": "123",
    "metadata": {...},
    "tags": ["github", "bug", "critical"]
  },
  "correlation_id": "abc-123",
  "timestamp": 1234567890.123
}
```

## Monitoring

### Metrics

The service exposes Prometheus metrics at `/metrics`:

```
webhook_requests_total{source="github",status="success"} 150
webhook_processing_duration_seconds{source="github"} 0.023
webhook_incidents_created_total{source="github",severity="critical"} 5
```

### Health Checks

Health endpoint at `/health`:

```json
{
  "status": "healthy",
  "service": "webhook-service",
  "supported_sources": ["github", "jira", "servicenow", "prometheus"],
  "timestamp": 1234567890
}
```

### Logging

All webhook processing is logged with correlation IDs for tracing:

```
INFO WebhookService Processed github webhook: GitHub Issue: Critical Bug
INFO WebhookAPI Successfully processed github webhook: GitHub Issue: Critical Bug
```

## Security

### Signature Validation

- **GitHub**: HMAC-SHA256 signature validation
- **Jira**: Configurable signature validation
- **ServiceNow**: Optional signature validation

### Authentication

All webhook endpoints require API key authentication via the `Authorization` header.

### Rate Limiting

Built-in rate limiting prevents webhook spam and abuse.

## Development

### Running Tests

```bash
pytest tests/test_webhook_service.py -v
```

### Adding New Webhook Sources

1. Create a new processor class inheriting from `WebhookProcessor`
2. Implement `validate_signature()` and `process_event()` methods
3. Register the processor in `WebhookService._register_processors()`
4. Add API endpoint in `api.py`
5. Update documentation

### Example Custom Processor

```python
class CustomWebhookProcessor(WebhookProcessor):
    def __init__(self):
        super().__init__(WebhookSource.CUSTOM)

    def validate_signature(self, payload, signature, secret):
        # Implement custom validation logic
        return True

    def process_event(self, event):
        # Implement custom event processing
        return ProcessedIncident(...)
```

## Troubleshooting

### Common Issues

1. **Signature validation fails**
   - Check webhook secret configuration
   - Verify signature header format

2. **Webhooks not processing**
   - Check API key authentication
   - Verify payload format
   - Check service logs

3. **Incidents not created**
   - Verify webhook meets severity criteria
   - Check message queue connectivity

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m webhook_service.app
```

### Testing Webhooks

Use curl to test webhook endpoints:

```bash
curl -X POST http://localhost:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"test": "payload"}'