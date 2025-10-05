# Brain Swarm Helm Chart

A comprehensive Helm chart for deploying Brain Swarm with enterprise-grade security, monitoring, and scalability features.

## Features

- 🏗️ **Modular Architecture**: Deploy API, operations server, and microservices independently
- 🔒 **Enterprise Security**: Rate limiting, IP whitelisting, TLS encryption
- 📊 **Comprehensive Monitoring**: Prometheus metrics, Grafana dashboards, alerting
- 🚀 **High Availability**: Multi-cluster federation, auto-scaling, load balancing
- 🧠 **AI-Powered**: Knowledge Cortex with vector search and graph relationships
- 📚 **Developer Portal**: Interactive API documentation with MkDocs

## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- NGINX Ingress Controller or Traefik (for ingress)
- cert-manager (for TLS certificates, optional)

### Quick Start

```bash
# Add the repository
helm repo add brain-swarm https://jfbintecha.github.io/brain-swarm
helm repo update

# Install with default settings
helm install brain-swarm brain-swarm/brain-swarm

# Install with custom values
helm install brain-swarm brain-swarm/brain-swarm -f my-values.yaml
```

### Production Deployment

```bash
# Create namespace
kubectl create namespace brainswarm

# Install with production values
helm install brain-swarm brain-swarm/brain-swarm \
  --namespace brainswarm \
  --set ingress.enabled=true \
  --set ingress.host=api.brain-swarm.company.com \
  --set ingress.security.ipWhitelist='["10.0.0.0/8","172.16.0.0/12"]' \
  --set cortex.enabled=true
```

## Configuration

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global image pull secrets | `[]` |
| `global.storageClass` | Global storage class | `""` |

### API Server Configuration

```yaml
api:
  enabled: true
  replicaCount: 3  # For high availability

  image:
    repository: brain-swarm
    tag: "1.0.0"

  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi

  config:
    environment: production
    node:
      swarmId: "production-swarm"
      maxAgents: 50
      maxAgentLoad: 5
    scalability:
      enabled: true
      messageQueueMode: "cluster"
      redisUrls: ["redis://brain-swarm-redis:6379"]
      asyncAgentsEnabled: true
      autoScalingEnabled: true
```

### Ingress Configuration

#### NGINX Ingress (Default)

```yaml
ingress:
  enabled: true
  traefikEnabled: false
  className: "nginx"
  host: "api.brain-swarm.company.com"
  certManagerIssuer: "letsencrypt-prod"

  tls:
    enabled: true
    secretName: "brain-swarm-api-tls"

  security:
    rateLimit:
      average: 10  # Requests per second
      burst: 20    # Burst capacity

    ipWhitelist:
      - "10.0.0.0/8"      # Internal network
      - "172.16.0.0/12"   # Private networks
      - "192.168.0.0/16"  # Private networks

    metricsIPWhitelist:
      - "10.0.0.0/8"      # Restrictive metrics access
```

#### Traefik Ingress

```yaml
ingress:
  enabled: true
  traefikEnabled: true
  certResolver: "letsencrypt"
  host: "api.brain-swarm.company.com"

  security:
    rateLimit:
      average: 10
      burst: 20

    ipWhitelist:
      - "10.0.0.0/8"
      - "203.0.113.0/24"  # Monitoring subnet
```

### Security Features

#### Rate Limiting

The ingress automatically applies rate limiting to protect against abuse:

- **API Endpoints**: Configurable RPS limits with burst capacity
- **Metrics Endpoints**: Stricter limits for monitoring endpoints
- **Health Checks**: Unlimited access for load balancer health checks

#### IP Whitelisting

Restrict access to specific IP ranges:

```yaml
ingress:
  security:
    ipWhitelist:
      - "10.0.0.0/8"      # Internal corporate network
      - "203.0.113.0/24"  # Monitoring and CI/CD systems
      - "198.51.100.0/24" # External partners

    metricsIPWhitelist:
      - "10.0.0.0/8"      # Only internal access to metrics
```

#### Security Headers

Automatic security headers are applied:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Knowledge Cortex

Enable AI-powered knowledge management:

```yaml
cortex:
  enabled: true

  chroma:
    enabled: true
    persistence:
      enabled: true
      size: 50Gi

  s3:
    enabled: true
    bucket: "brain-swarm-knowledge"
    region: "us-east-1"

  summarizer:
    enabled: true
    schedule: "*/15 * * * *"  # Every 15 minutes
```

### Monitoring Stack

```yaml
monitoring:
  grafana:
    enabled: true

  prometheus:
    enabled: true

  alertmanager:
    enabled: true
    smtp:
      enabled: true
      smarthost: "smtp.company.com:587"
      from: "alerts@brain-swarm.company.com"

    slack:
      enabled: true
      webhookUrl: "https://hooks.slack.com/services/..."
      channel: "#brain-swarm-alerts"
```

## Usage Examples

### Basic API Access

```bash
# Get cluster health
curl https://api.brain-swarm.company.com/health

# Access API documentation
open https://api.brain-swarm.company.com/docs

# Check metrics (if IP whitelisted)
curl https://api.brain-swarm.company.com/metrics
```

### Task Management

```bash
# Create a task
curl -X POST https://api.brain-swarm.company.com/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Analyze system performance",
    "type": "analysis",
    "priority": 2
  }'

# Check task status
curl https://api.brain-swarm.company.com/tasks/task_123
```

### Federation Management

```bash
# List available swarms
curl https://api.brain-swarm.company.com/federation/swarms

# Check federation health
curl https://api.brain-swarm.company.com/federation/health
```

## Security Best Practices

### Network Security

1. **Enable TLS**: Always use `ingress.tls.enabled=true`
2. **IP Whitelisting**: Restrict access to known networks
3. **Rate Limiting**: Configure appropriate limits for your environment
4. **Network Policies**: Use Kubernetes network policies for pod-to-pod traffic

### Authentication & Authorization

1. **JWT Tokens**: Use secure JWT secrets in production
2. **API Keys**: Rotate API keys regularly
3. **RBAC**: Configure proper role-based access control

### Monitoring & Alerting

1. **Enable All Monitoring**: Set `monitoring.*.enabled=true`
2. **Configure Alerts**: Set up appropriate alert thresholds
3. **Log Aggregation**: Integrate with your logging stack
4. **Regular Audits**: Monitor access patterns and anomalies

## Troubleshooting

### Common Issues

#### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n brainswarm

# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

#### Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n brainswarm

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

#### Rate Limiting Too Restrictive

```yaml
# Adjust rate limits in values.yaml
ingress:
  security:
    rateLimit:
      average: 50  # Increase RPS limit
      burst: 100   # Increase burst capacity
```

#### IP Whitelist Blocking Legitimate Access

```yaml
# Add your IP range
ingress:
  security:
    ipWhitelist:
      - "203.0.113.0/24"  # Your office network
```

### Debug Commands

```bash
# Check pod status
kubectl get pods -n brainswarm

# Check service endpoints
kubectl get endpoints -n brainswarm

# Check ingress configuration
kubectl describe ingress brain-swarm-api -n brainswarm

# Test connectivity
kubectl run test --image=curlimages/curl --rm -it --restart=Never \
  -- curl -v https://api.brain-swarm.company.com/health
```

## Scaling

### Horizontal Scaling

```yaml
api:
  replicaCount: 5

operations:
  replicaCount: 3

# Enable auto-scaling
api:
  config:
    scalability:
      autoScalingEnabled: true
      agentPoolMin: 5
      agentPoolMax: 50
```

### Multi-Cluster Federation

```yaml
api:
  config:
    scalability:
      multiClusterEnabled: true
      clusterId: "us-east-1"
      clusterRole: "primary"
```

## Backup & Recovery

### Knowledge Cortex Backup

```bash
# Backup ChromaDB data
kubectl exec -n brainswarm deployment/brain-swarm-chroma -- \
  pg_dump -U chroma chroma > chroma_backup.sql

# Backup S3 data (if using S3 archive)
aws s3 sync s3://brain-swarm-knowledge ./backup/
```

### Configuration Backup

```bash
# Backup Helm values
helm get values brain-swarm -n brainswarm > backup-values.yaml

# Backup secrets
kubectl get secrets -n brainswarm -o yaml > secrets-backup.yaml
```

## Contributing

Please see the main [Brain Swarm repository](https://github.com/jfbinTECHA/brain-swarm) for contribution guidelines.

## License

This Helm chart is part of the Brain Swarm project.