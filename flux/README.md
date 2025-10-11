# Flux GitOps Deployment

This directory contains Flux manifests for pure GitOps deployment of Brain Swarm Ops.

## Flux vs Argo CD

| Aspect | Flux | Argo CD |
|--------|------|---------|
| **Philosophy** | Pure GitOps | GitOps with UI |
| **Learning Curve** | Steeper | Moderate |
| **Multi-cluster** | Excellent | Excellent |
| **RBAC** | Basic | Advanced |
| **UI** | None (CLI only) | Rich web UI |
| **Ecosystem** | CNCF project | Argo project |

## Installation

### Bootstrap Flux
```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux in cluster
flux bootstrap github \
  --owner=jfbinTECHA \
  --repository=brain-swarm \
  --branch=main \
  --path=./flux \
  --personal
```

### Deploy Application
```bash
# Deploy development environment
kubectl apply -f flux/brain-swarm-dev.yaml

# Deploy production environment
kubectl apply -f flux/brain-swarm-prod.yaml
```

## Manifest Structure

### Development Environment (`brain-swarm-dev.yaml`)
- **Target**: Development cluster/namespace
- **Sync Policy**: Automated with fast reconciliation
- **Features**: Lightweight resources, no ingress, disabled monitoring

### Production Environment (`brain-swarm-prod.yaml`)
- **Target**: Production cluster/namespace
- **Sync Policy**: Automated with validation
- **Features**: Full production settings, ingress enabled, HPA, monitoring

### GitRepository
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: GitRepository
metadata:
  name: brain-swarm
spec:
  interval: 1m
  url: https://github.com/jfbinTECHA/brain-swarm
  ref:
    branch: main
```

### HelmRelease
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: brain-swarm
spec:
  interval: 5m
  chart:
    spec:
      chart: helm/brain-swarm
      sourceRef:
        kind: GitRepository
        name: brain-swarm
  valuesFrom:
    - kind: ConfigMap
      name: brain-swarm-dev-values
```

## Operations

### Check Status
```bash
# View all resources
flux get all

# Check specific resources
flux get sources git
flux get helmreleases

# View logs
flux logs --follow --all-namespaces
```

### Manual Sync
```bash
# Reconcile all resources
flux reconcile source git brain-swarm
flux reconcile helmrelease brain-swarm
```

### Troubleshooting
```bash
# Check resource status
kubectl get gitrepositories,kustomizations,helmreleases -A

# View detailed status
flux describe helmrelease brain-swarm

# Check Flux controller logs
kubectl logs -n flux-system deployment/source-controller
kubectl logs -n flux-system deployment/helm-controller
```

## Configuration Management

### Values Override
```yaml
# ConfigMap with custom values
apiVersion: v1
kind: ConfigMap
metadata:
  name: brain-swarm-dev-values
data:
  values.yaml: |
    bridge:
      ingress:
        enabled: false
    cortex:
      hpa:
        enabled: false
```

### Environment-Specific Deployments
```bash
# Create separate directories for environments
flux/                    # Development
flux/production/         # Production configs
flux/staging/           # Staging configs
```

## Security Considerations

### Image Signing
```yaml
# Enable image verification
spec:
  chart:
    spec:
      verify:
        provider: cosign
        secretRef:
          name: cosign-public-key
```

### Secret Management
- Use external secret management (External Secrets Operator)
- Never store secrets in Git
- Use sealed secrets or similar

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/flux-sync.yaml
name: Flux Sync
on:
  push:
    branches: [main]
    paths:
      - 'helm/**'
      - 'flux/**'
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Sync Flux
        run: |
          flux create source git brain-swarm \
            --url=https://github.com/jfbinTECHA/brain-swarm \
            --branch=main \
            --interval=1m
```

## Migration from Manual

### From Helm CLI
```bash
# Current manual deployment
helm upgrade --install brain-swarm ./helm/brain-swarm -f values.yaml

# Migrate to Flux
kubectl apply -f flux/
# Flux takes over management
```

### Rollback
```bash
# Flux rollback (if supported)
flux suspend helmrelease brain-swarm
# Edit GitRepository to point to previous commit
flux resume helmrelease brain-swarm

# Or Git-based rollback
git revert <commit>
git push origin main
```

## Best Practices

- **GitOps First**: Treat Flux as the source of truth
- **Immutable Configs**: Store all configuration in Git
- **Automated Testing**: Validate manifests before commit
- **Monitoring**: Set up alerts for reconciliation failures
- **Documentation**: Keep operational docs in Git
- **Branch Strategy**: Use branches for environment isolation

## Comparison with Argo CD

Choose **Flux** if you prefer:
- Pure GitOps without UI dependencies
- CNCF project with strong community
- Advanced Git integration features
- Lower operational overhead

Choose **Argo CD** if you need:
- Rich web UI for operations teams
- Advanced RBAC and multi-tenancy
- Easier learning curve
- Better visualization of application health