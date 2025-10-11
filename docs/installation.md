# 🚀 Installation Guide

## Prerequisites

Before installing BrainSwarmOps, ensure your environment meets these requirements:

### Kubernetes Cluster
- **Version**: Kubernetes 1.24+ (tested on 1.25-1.28)
- **Nodes**: Minimum 3 nodes for high availability
- **Resources**: 4 CPU cores, 8GB RAM minimum per node

### Helm
- **Version**: Helm 3.8+
- **Repository Access**: Internet access for chart downloads

### Ingress Controller
Choose one of the following ingress controllers:

#### NGINX Ingress Controller (Recommended)
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx
```

#### Traefik Ingress Controller
```bash
helm repo add traefik https://helm.traefik.io/traefik
helm install traefik traefik/traefik
```

### External Dependencies

#### Redis (Required)
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis --set auth.enabled=false
```

#### PostgreSQL (Optional, for advanced features)
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgresql bitnami/postgresql
```

## Quick Start Installation

### 1. Add Helm Repository
```bash
helm repo add brain-swarm https://brain-swarm.github.io/helm-charts
helm repo update
```

### 2. Create Namespace
```bash
kubectl create namespace brainswarm
```

### 3. Install BrainSwarmOps
```bash
helm install brain-swarm brain-swarm/brain-swarm \
  --namespace brainswarm \
  --set ticketBridge.enabled=true \
  --set ticketBridge.ingress.enabled=true \
  --set ticketBridge.ingress.host=webhooks.brainswarm.ai
```

### 4. Verify Installation
```bash
# Check pod status
kubectl get pods -n brainswarm

# Check services
kubectl get svc -n brainswarm

# Check ingress
kubectl get ingress -n brainswarm
```

## Advanced Installation

### Production Configuration

Create a `values-production.yaml` file:

```yaml
# values-production.yaml
global:
  imageRegistry: "your-registry.com"

api:
  replicaCount: 3
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi

grafana:
  enabled: true
  adminPassword: "secure-password-here"
  persistence:
    enabled: true
    size: 50Gi

prometheus:
  enabled: true
  persistence:
    enabled: true
    size: 100Gi

ticketBridge:
  enabled: true
  ingress:
    enabled: true
    host: "webhooks.production.brainswarm.ai"
    className: "nginx"
    tls:
      enabled: true
      secretName: "brainswarm-tls"

# Security configuration
securityContext:
  runAsNonRoot: true
  runAsUser: 1001

podSecurityContext:
  fsGroup: 1001
```

Install with production values:
```bash
helm install brain-swarm brain-swarm/brain-swarm \
  --namespace brainswarm \
  --values values-production.yaml
```

### High Availability Setup

For production environments with high availability:

```yaml
# High availability configuration
api:
  replicaCount: 3
  pdb:
    enabled: true
    minAvailable: 2

grafana:
  replicas: 2

prometheus:
  replicas: 2

redis:
  replica:
    replicaCount: 3
```

### Multi-Cluster Federation

For multi-cluster deployments:

```yaml
federation:
  enabled: true
  clusters:
    - name: "us-east"
      apiServer: "https://api.us-east.k8s.example.com"
    - name: "us-west"
      apiServer: "https://api.us-west.k8s.example.com"
```

## Post-Installation Configuration

### 1. DNS Configuration

Configure DNS records for your ingress hosts:

```bash
# Example DNS records
webhooks.brainswarm.ai    A     1.2.3.4
grafana.brainswarm.ai     A     1.2.3.4
api.brainswarm.ai         A     1.2.3.4
```

### 2. TLS Certificate Setup

#### Let's Encrypt (Automatic)
```yaml
ticketBridge:
  ingress:
    certManagerIssuer: "letsencrypt-prod"
    tls:
      enabled: true
```

#### Custom Certificate
```yaml
ticketBridge:
  ingress:
    tls:
      enabled: true
      secretName: "custom-tls-secret"
```

Create the TLS secret:
```bash
kubectl create secret tls custom-tls-secret \
  --cert=tls.crt \
  --key=tls.key \
  --namespace brainswarm
```

### 3. External Service Integration

#### GitHub Webhook Configuration
1. Go to your GitHub repository → Settings → Webhooks
2. Add webhook URL: `https://webhooks.brainswarm.ai/gh-webhook`
3. Content type: `application/json`
4. Secret: Configure in Kubernetes secrets

#### Jira Webhook Configuration
1. Go to Jira → System → WebHooks
2. URL: `https://webhooks.brainswarm.ai/jira-webhook`
3. Events: Issue created, updated, resolved

#### ServiceNow Integration
1. Create REST API endpoint in ServiceNow
2. Configure webhook URL: `https://webhooks.brainswarm.ai/servicenow-webhook`
3. Set up authentication tokens

### 4. PagerDuty/OpsGenie Setup

#### PagerDuty Integration
```bash
# Create service integration
curl -X POST \
  https://api.pagerduty.com/services \
  -H "Authorization: Token token=YOUR_API_TOKEN" \
  -d '{
    "service": {
      "name": "BrainSwarmOps",
      "integration": {
        "type": "events_api_v2_inbound_integration"
      }
    }
  }'
```

#### OpsGenie Integration
```bash
# Create API integration
curl -X POST \
  https://api.opsgenie.com/v2/integrations \
  -H "Authorization: GenieKey YOUR_API_KEY" \
  -d '{
    "name": "BrainSwarmOps",
    "type": "API"
  }'
```

## Access and Verification

### Access Grafana
```bash
# Port forward (for local access)
kubectl port-forward svc/brain-swarm-grafana 3000:80 -n brainswarm

# Access at: http://localhost:3000
# Default credentials: admin / [configured password]
```

### Access API
```bash
# Port forward API
kubectl port-forward svc/brain-swarm-api 8000:8000 -n brainswarm

# Test API health
curl http://localhost:8000/health
```

### Test Webhook Endpoints
```bash
# Test GitHub webhook
curl -X POST https://webhooks.brainswarm.ai/gh-webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'

# Expected response: HTTP 200 with validation message
```

## Troubleshooting Installation

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n brainswarm

# Check logs
kubectl logs <pod-name> -n brainswarm

# Check resource constraints
kubectl describe nodes
```

#### Ingress Not Working
```bash
# Check ingress status
kubectl describe ingress brain-swarm-ticket-bridge -n brainswarm

# Check ingress controller
kubectl get pods -n ingress-nginx

# Test connectivity
curl -I https://webhooks.brainswarm.ai/gh-webhook
```

#### Certificate Issues
```bash
# Check certificate status
kubectl get certificate -n brainswarm

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### Health Checks

#### System Health
```bash
# Overall system health
kubectl get pods -n brainswarm
kubectl get svc -n brainswarm
kubectl get ingress -n brainswarm
```

#### Application Health
```bash
# API health
curl https://api.brainswarm.ai/health

# Grafana health
curl https://grafana.brainswarm.ai/api/health
```

## Upgrading

### Minor Version Upgrades
```bash
helm repo update
helm upgrade brain-swarm brain-swarm/brain-swarm -n brainswarm
```

### Major Version Upgrades
```bash
# Backup current configuration
helm get values brain-swarm -n brainswarm > backup-values.yaml

# Upgrade with backup
helm upgrade brain-swarm brain-swarm/brain-swarm \
  --namespace brainswarm \
  --values backup-values.yaml \
  --version 2.0.0
```

## Uninstalling

### Complete Removal
```bash
# Uninstall Helm release
helm uninstall brain-swarm -n brainswarm

# Remove namespace (optional)
kubectl delete namespace brainswarm

# Clean up PVCs (if persistent data should be removed)
kubectl delete pvc -l app.kubernetes.io/instance=brain-swarm -n brainswarm
```

### Selective Removal
```bash
# Remove specific components
helm upgrade brain-swarm brain-swarm/brain-swarm \
  --namespace brainswarm \
  --set grafana.enabled=false \
  --set prometheus.enabled=false
```

## Support and Resources

- **Documentation**: [docs.brainswarm.ai](https://docs.brainswarm.ai)
- **GitHub Issues**: [Report bugs](https://github.com/brain-swarm/brain-swarm-ops/issues)
- **Community**: [GitHub Discussions](https://github.com/brain-swarm/brain-swarm-ops/discussions)
- **Professional Support**: [enterprise@brainswarm.ai](mailto:enterprise@brainswarm.ai)