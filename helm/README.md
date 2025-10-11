# Brain Swarm Helm Charts

This directory contains Helm charts for deploying Brain Swarm on Kubernetes.

## Chart Structure

```
helm/
├── brain-swarm/          # Main Brain Swarm chart
│   ├── Chart.yaml        # Chart metadata and dependencies
│   ├── values.yaml       # Default configuration values
│   ├── values-production.yaml  # Production-optimized values
│   ├── templates/        # Kubernetes resource templates
│   │   ├── _helpers.tpl  # Template helper functions
│   │   ├── deployment-api.yaml
│   │   ├── service-api.yaml
│   │   ├── cortex-pvc.yaml
│   │   ├── chroma-deployment.yaml
│   │   ├── chroma-service.yaml
│   │   ├── chroma-pvc.yaml
│   │   ├── grafana-dashboard.yaml
│   │   ├── grafana-dashboard-cortex-incident-board.yaml
│   │   ├── prometheus-alerts.yaml
│   │   ├── alertmanager-config.yaml
│   │   ├── summarizer-cronjob.yaml
│   │   ├── swarmops-hook-deployment.yaml
│   │   ├── swarmops-hook-service.yaml
│   │   ├── swarmops-hook-kilo-deployment.yaml
│   │   ├── swarmops-hook-kilo-service.yaml
│   │   ├── swarmops-ticket-bridge-deployment.yaml
│   │   ├── swarmops-ticket-bridge-service.yaml
│   │   ├── swarmops-ticket-bridge-ingress.yaml
│   │   ├── swarmops-ticket-bridge-ingressroute.yaml
│   │   ├── swarmops-ticket-sync-deployment.yaml
│   │   ├── swarmview-deployment.yaml
│   │   ├── swarmview-service.yaml
│   │   ├── crd-brainswarmcluster.yaml
│   │   └── swarmops-hook.yaml
│   └── charts/           # Subchart dependencies
└── README.md            # This file
```

## Components

### Core Services
- **API Service**: Main FastAPI application with REST endpoints
- **Cortex**: Incident processing and AI orchestration
- **Chroma**: Vector database for embeddings
- **Grafana**: Visualization dashboards
- **Prometheus**: Metrics collection and alerting

### Integration Services
- **SwarmOps Hook**: ServiceNow integration webhook
- **Ticket Bridge**: Bidirectional ticket synchronization
- **SwarmView**: Real-time swarm monitoring dashboard

### Infrastructure
- **PVCs**: Persistent volume claims for data persistence
- **Services**: Kubernetes service definitions
- **ConfigMaps**: Configuration management
- **Secrets**: Secure credential management

## Installation

### Prerequisites
- Kubernetes 1.19+
- Helm 3.0+
- Persistent volumes for data persistence

### Quick Start

```bash
# Add the Brain Swarm Helm repository
helm repo add brain-swarm https://jfbintecha.github.io/brain-swarm
helm repo update

# Install with default values
helm install brain-swarm brain-swarm/brain-swarm

# Install with custom values
helm install brain-swarm brain-swarm/brain-swarm -f values-production.yaml
```

### Production Deployment

```bash
# Install with production values
helm install brain-swarm brain-swarm/brain-swarm \
  --namespace brain-swarm \
  --create-namespace \
  -f helm/brain-swarm/values-production.yaml \
  --set image.tag=v1.0.0
```

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image repository | `jfbintecha/brain-swarm` |
| `image.tag` | Docker image tag | `latest` |
| `replicaCount` | Number of API replicas | `1` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `ingress.enabled` | Enable ingress | `false` |
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `10Gi` |

### Scalability Settings

```yaml
# values-production.yaml
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

scalability:
  enabled: true
  messageQueueMode: "cluster"
  asyncAgentsEnabled: true
  multiClusterEnabled: true
  autoScalingEnabled: true
```

## Development

### Local Development with Helm

```bash
# Install locally for development
helm install brain-swarm ./helm/brain-swarm \
  --set image.tag=dev \
  --set persistence.enabled=false
```

### Template Debugging

```bash
# Render templates without installing
helm template brain-swarm ./helm/brain-swarm

# Debug with values
helm template brain-swarm ./helm/brain-swarm -f values-production.yaml
```

## Custom Resource Definitions

The chart includes a custom resource definition for Brain Swarm clusters:

```yaml
apiVersion: brain-swarm.dev/v1
kind: BrainSwarmCluster
metadata:
  name: production-cluster
spec:
  replicas: 3
  version: "1.0.0"
  federation:
    enabled: true
    clusters:
      - name: "us-east"
      - name: "us-west"
```

## Monitoring

### Built-in Monitoring

The chart includes pre-configured:
- **Prometheus metrics** collection
- **Grafana dashboards** for visualization
- **AlertManager** rules for notifications
- **Health checks** and probes

### Accessing Dashboards

```bash
# Port forward Grafana
kubectl port-forward svc/brain-swarm-grafana 3000:80

# Open http://localhost:3000
# Default credentials: admin/admin
```

## Troubleshooting

### Common Issues

1. **PVC Pending**: Check storage class availability
   ```bash
   kubectl get storageclass
   ```

2. **Pod CrashLoopBackOff**: Check logs
   ```bash
   kubectl logs -f deployment/brain-swarm-api
   ```

3. **Service Unavailable**: Check service endpoints
   ```bash
   kubectl get endpoints
   ```

### Logs and Debugging

```bash
# View all pod logs
kubectl logs -l app.kubernetes.io/name=brain-swarm

# Debug with temporary pod
kubectl run debug --image=busybox --rm -it -- sh
```

## Contributing

When modifying Helm templates:

1. Update `Chart.yaml` version for releases
2. Test templates with `helm template`
3. Validate with `helm lint`
4. Update this README for new features

## Version History

- **v1.0.0**: Enterprise Incident Response Platform
  - Multi-cluster federation
  - AI-driven triage
  - Comprehensive observability
  - ServiceNow integration

- **v0.1.0**: Initial Helm chart
  - Basic deployment templates
  - Core service definitions
  - Development configuration