# ⚙️ Configuration Guide

## Helm Values Reference

BrainSwarmOps is configured using Helm values. This guide covers all available configuration options.

## Global Configuration

```yaml
global:
  # Global image registry
  imageRegistry: ""
  # Global image pull secrets
  imagePullSecrets: []
  # Global storage class
  storageClass: ""
```

## API Configuration

```yaml
api:
  # Enable/disable API component
  enabled: true
  # Number of replicas
  replicaCount: 1

  image:
    repository: brain-swarm
    tag: "latest"
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 8000
    annotations: {}

  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi

  # Application configuration
  config:
    environment: production
    node:
      swarmId: "default-swarm"
      host: "0.0.0.0"
      port: 8000
      maxAgents: 10
      maxAgentLoad: 3

    database:
      url: "sqlite:///data/brain_swarm.db"

    logging:
      level: INFO

    federation:
      enabled: false

    scalability:
      enabled: false
      messageQueueMode: "single_node"
      redisUrls: ["redis://redis:6379"]
      partitions: 8
      asyncAgentsEnabled: false
      agentPoolMin: 1
      agentPoolMax: 10
      loadBalancingStrategy: "least_loaded"
      multiClusterEnabled: false
      clusterId: "default-cluster"
      clusterRole: "primary"
      autoScalingEnabled: false

    security:
      jwtSecret: "change-this-in-production"
      jwtAlgorithm: "HS256"
      jwtExpirationHours: 24

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Ticket Bridge Configuration

```yaml
ticketBridge:
  # Enable/disable ticket bridge
  enabled: true
  # Number of replicas
  replicaCount: 1

  image:
    repository: brain-swarm-swarmops-hook
    tag: "latest"
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 8080
    nodePort: ""

  # Ingress configuration
  ingress:
    enabled: false
    traefikEnabled: false
    className: "nginx"
    host: "bridge.brainswarm.local"
    certManagerIssuer: "letsencrypt-prod"

    # NGINX-specific settings
    whitelist: "192.30.252.0/22,185.199.108.0/22,140.82.112.0/20,104.192.136.0/21,18.205.93.0/25"

    # Traefik-specific settings
    allowedCIDRs:
      - 192.30.252.0/22  # GitHub
      - 185.199.108.0/22  # GitHub
      - 140.82.112.0/20  # GitHub
      - 104.192.136.0/21  # GitHub
      - 18.205.93.0/25   # Atlassian

    annotations: {}
    tls:
      enabled: true
      secretName: ""

  # AI API configuration
  brainSwarmApiUrl: "http://brain-swarm-api.brainswarm.svc.cluster.local:8000"

  # Environment variable overrides
  extraEnvVars: []

  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Grafana Configuration

```yaml
grafana:
  # Enable/disable Grafana
  enabled: false
  # Number of replicas
  replicas: 1

  image:
    repository: grafana/grafana
    tag: "9.5.0"
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 80

  # Root URL for Grafana
  rootUrl: ""

  # Admin password (change in production!)
  adminPassword: "admin"

  # Persistence configuration
  persistence:
    enabled: true
    size: 10Gi

  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Prometheus Configuration

```yaml
prometheus:
  # Enable/disable Prometheus
  enabled: false
  # Number of replicas
  replicas: 1

  image:
    repository: prom/prometheus
    tag: "v2.40.0"
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 9090

  # Persistence configuration
  persistence:
    enabled: true
    size: 50Gi

  # Retention period
  retention: "30d"

  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Redis Configuration

```yaml
redis:
  # Enable/disable Redis
  enabled: true

  image:
    repository: redis
    tag: "7-alpine"
    pullPolicy: IfNotPresent

  service:
    port: 6379

  # Authentication
  auth:
    enabled: false

  # Persistence
  persistence:
    enabled: true
    size: 8Gi

  resources:
    limits:
      cpu: 500m
      memory: 256Mi
    requests:
      cpu: 100m
      memory: 128Mi

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Cortex Configuration

```yaml
cortex:
  # Enable/disable Cortex
  enabled: false

  # Scheduled summarizer
  summarizer:
    enabled: true
    schedule: "*/15 * * * *"

  # ChromaDB configuration
  chroma:
    enabled: true
    image:
      repository: chromadb/chroma
      tag: "0.4.18"
      pullPolicy: IfNotPresent
    service:
      port: 8000
    persistence:
      enabled: true
      size: 10Gi

  # S3 configuration (optional)
  s3:
    enabled: false
    bucket: "brain-swarm-cortex"
    region: "us-east-1"
    endpointUrl: ""

  # Cortex persistence
  persistence:
    enabled: true
    size: 20Gi

  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi

  nodeSelector: {}
  tolerations: []
  affinity: {}
```

## Security Configuration

```yaml
# Pod security context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1001
  fsGroup: 1001

# Container security context
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1001
  capabilities:
    drop:
    - ALL

# Service account
serviceAccount:
  create: true
  annotations: {}
  name: ""
```

## Network Policies

```yaml
networkPolicy:
  enabled: false

  # Default deny all ingress
  defaultDenyIngress: true

  # Allow specific ingress rules
  ingressRules:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080

  # Allow specific egress rules
  egressRules:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443  # HTTPS for external APIs
        - protocol: TCP
          port: 80   # HTTP fallback
```

## Monitoring Configuration

```yaml
monitoring:
  # ServiceMonitor for Prometheus
  serviceMonitor:
    enabled: true
    interval: 30s
    scrapeTimeout: 10s

  # PrometheusRule for alerting
  prometheusRule:
    enabled: true
    rules:
      - alert: BrainSwarmHighIncidentRate
        expr: rate(cortex_incident_event_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High incident rate detected"
          description: "Incident rate is {{ $value }} per minute"

  # Grafana dashboards
  grafana:
    dashboards:
      enabled: true
      configMapName: brain-swarm-grafana-dashboards
```

## Example Configurations

### Minimal Development Setup

```yaml
ticketBridge:
  enabled: true
  ingress:
    enabled: true
    host: "webhooks.dev.brainswarm.ai"

grafana:
  enabled: true
  adminPassword: "dev-password"

prometheus:
  enabled: true
```

### Production Setup

```yaml
global:
  imageRegistry: "your-registry.com"

api:
  replicaCount: 3
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi

ticketBridge:
  enabled: true
  replicaCount: 2
  ingress:
    enabled: true
    host: "webhooks.brainswarm.ai"
    tls:
      enabled: true
      secretName: "brainswarm-tls"

grafana:
  enabled: true
  replicas: 2
  adminPassword: "secure-production-password"
  persistence:
    size: 50Gi

prometheus:
  enabled: true
  replicas: 2
  persistence:
    size: 100Gi
  retention: "90d"

securityContext:
  runAsNonRoot: true
  runAsUser: 1001

networkPolicy:
  enabled: true
```

### High Availability Setup

```yaml
api:
  replicaCount: 3

ticketBridge:
  replicaCount: 3

grafana:
  replicas: 2

prometheus:
  replicas: 2

redis:
  replica:
    replicaCount: 3

# Affinity rules for high availability
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - brain-swarm
        topologyKey: kubernetes.io/hostname
```

## Environment Variables

### Ticket Bridge Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Service port | `8080` |
| `DEFAULT_TICKET_SYSTEM` | Default ticket system | `jira` |
| `CRITICAL_TICKET_SYSTEM` | Critical incident system | `jira` |
| `JIRA_ENABLED` | Enable Jira integration | `false` |
| `GITHUB_ENABLED` | Enable GitHub integration | `false` |
| `SERVICENOW_ENABLED` | Enable ServiceNow integration | `false` |
| `BRAIN_SWARM_API_URL` | AI API endpoint | `http://brain-swarm-api.brainswarm.svc.cluster.local:8000` |
| `BRAIN_SWARM_API_TOKEN` | AI API authentication | `` |

### API Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `SWARM_ID` | Swarm identifier | `default-swarm` |
| `DATABASE_URL` | Database connection | `sqlite:///data/brain_swarm.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `JWT_SECRET` | JWT signing secret | `change-this-in-production` |
| `REDIS_URL` | Redis connection | `redis://redis:6379` |

## Configuration Validation

### Pre-deployment Validation

```bash
# Validate Helm chart
helm template brain-swarm ./helm/brain-swarm --dry-run

# Check for configuration errors
helm lint ./helm/brain-swarm

# Validate Kubernetes manifests
kubectl apply --dry-run=client -f <generated-manifests>
```

### Runtime Validation

```bash
# Check configuration loading
kubectl logs deployment/brain-swarm-ticket-bridge -n brainswarm | grep "configuration"

# Validate service connectivity
kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- curl http://localhost:8080/health

# Check environment variables
kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- env | grep BRAIN_SWARM
```

## Troubleshooting Configuration

### Common Configuration Issues

#### Environment Variables Not Set
```bash
# Check pod environment
kubectl exec -it <pod-name> -n brainswarm -- env

# Verify ConfigMap/Secret mounting
kubectl describe pod <pod-name> -n brainswarm
```

#### Ingress Not Routing Correctly
```bash
# Check ingress configuration
kubectl describe ingress brain-swarm-ticket-bridge -n brainswarm

# Test ingress controller
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

#### Persistence Issues
```bash
# Check PVC status
kubectl get pvc -n brainswarm

# Verify storage class
kubectl get storageclass

# Check mount points
kubectl exec -it <pod-name> -n brainswarm -- df -h
```

#### Resource Constraints
```bash
# Check resource usage
kubectl top pods -n brainswarm

# Review resource limits
kubectl describe pod <pod-name> -n brainswarm

# Adjust limits if needed
kubectl patch deployment <deployment-name> -n brainswarm --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "1000m"}]'
```

## Advanced Configuration

### Custom Metrics and Monitoring

```yaml
monitoring:
  customMetrics:
    enabled: true
    interval: 15s
    metrics:
      - name: cortex_custom_metric
        help: "Custom BrainSwarmOps metric"
        type: gauge
        value: 1.0
```

### Custom Alert Rules

```yaml
monitoring:
  prometheusRule:
    rules:
      - alert: CustomIncidentAlert
        expr: cortex_incident_event_total{severity="critical"} > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Multiple critical incidents detected"
          description: "More than 5 critical incidents in 5 minutes"
```

### Integration Webhooks

```yaml
integrations:
  slack:
    enabled: true
    webhookUrl: "https://hooks.slack.com/services/..."
    channels:
      - "#incidents"
      - "#alerts"

  teams:
    enabled: true
    webhookUrl: "https://outlook.office.com/webhook/..."
    channels:
      - "Incidents"
      - "Alerts"
```

This configuration guide provides comprehensive coverage of all BrainSwarmOps settings. For additional support, refer to the [troubleshooting guide](troubleshooting.md) or community forums.