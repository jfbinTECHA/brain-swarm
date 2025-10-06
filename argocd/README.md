# Argo CD GitOps Deployment

This directory contains Argo CD Application manifests for declarative deployment of Brain Swarm Ops from Git.

## Applications Included

### Development Environment (`brain-swarm-dev.yaml`)
- **Target**: Development cluster/namespace
- **Sync Policy**: Automated with self-healing
- **Project**: `default` (relaxed policies)
- **Features**: Fast iterations, auto-sync enabled

### Production Environment (`brain-swarm-prod.yaml`)
- **Target**: Production cluster/namespace
- **Sync Policy**: Automated with validation
- **Project**: `production` (strict policies)
- **Features**: Schema validation, controlled rollouts

## Prerequisites

### Argo CD Installation
```bash
# Install Argo CD CLI
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd

# Install Argo CD in cluster
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Repository Setup
1. **Fork/Clone**: Ensure this repository is accessible to Argo CD
2. **Branch Protection**: Set up branch protection on `main`
3. **Webhooks**: Configure GitHub webhooks for automatic sync

## Installation

### Deploy Argo CD Applications
```bash
# Deploy development environment
kubectl apply -f argocd/brain-swarm-dev.yaml

# Deploy production environment
kubectl apply -f argocd/brain-swarm-prod.yaml
```

### Access Argo CD UI
```bash
# Port forward Argo CD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open https://localhost:8080
# Login with admin credentials
```

## Configuration

### Application Parameters
```yaml
spec:
  source:
    helm:
      parameters:
        - name: bridge.image
          value: jfbintecha/swarmops-hook:latest
        - name: cortex.image
          value: jfbintecha/knowledge-cortex:latest
```

### Sync Options
- **CreateNamespace**: Automatically creates target namespace
- **PrunePropagationPolicy**: `foreground` ensures proper cleanup
- **Validate**: Schema validation for production safety
- **Retry**: Automatic retry on sync failures

## Monitoring & Operations

### Check Application Status
```bash
# List applications
argocd app list

# Get application details
argocd app get brain-swarm-dev

# View sync status
argocd app get brain-swarm-dev --hard-refresh
```

### Manual Sync
```bash
# Force sync application
argocd app sync brain-swarm-dev

# Sync with prune
argocd app sync brain-swarm-dev --prune
```

### Troubleshooting
```bash
# View application logs
argocd app logs brain-swarm-dev

# Check resource status
kubectl get all -n brainswarm

# View Argo CD logs
kubectl logs -n argocd deployment/argocd-application-controller
```

## GitOps Workflow

### Development Workflow
1. **Develop**: Make changes to Helm charts/values
2. **Commit**: Push changes to `main` branch
3. **Auto-Sync**: Argo CD automatically deploys changes
4. **Verify**: Check application health in Argo CD UI

### Production Workflow
1. **PR**: Create pull request with changes
2. **Review**: Code review and testing
3. **Merge**: Merge to `main` branch
4. **Validation**: Argo CD validates and deploys
5. **Monitor**: Watch rollout in Argo CD dashboard

## Security Considerations

### RBAC Configuration
```yaml
# Create production project with restrictions
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  destinations:
    - namespace: brainswarm
      server: https://kubernetes.default.svc
  sourceRepos:
    - https://github.com/jfbinTECHA/brain-swarm
  clusterResourceWhitelist: []
```

### Secret Management
- Use external secret management (Vault, AWS Secrets Manager)
- Never store secrets in Git
- Use Argo CD's secret management plugins

## Integration with CI/CD

### GitHub Actions Integration
```yaml
# .github/workflows/argocd-sync.yaml
name: ArgoCD Sync
on:
  push:
    branches: [main]
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: ArgoCD Sync
        uses: argoproj-labs/argocd-action@v1
        with:
          server-url: ${{ secrets.ARGOCD_SERVER }}
          token: ${{ secrets.ARGOCD_TOKEN }}
          app-name: brain-swarm-dev
```

## Comparison with Flux

| Feature | Argo CD | Flux |
|---------|---------|------|
| UI | Rich web UI | CLI/GitOps native |
| Multi-cluster | Excellent | Excellent |
| RBAC | Advanced | Basic |
| GitOps | Declarative | Pure GitOps |
| Learning Curve | Moderate | Steep |

## Migration from Manual Deployment

### From Helm CLI
```bash
# Current manual deployment
helm upgrade --install brain-swarm ./helm/brain-swarm -f values-prod.yaml

# Migrate to Argo CD
kubectl apply -f argocd/brain-swarm-prod.yaml
# Argo CD takes over management
```

### Rollback Strategy
```bash
# Argo CD rollback
argocd app rollback brain-swarm-prod HEAD-1

# Or rollback via Git
git revert <commit>
git push origin main
```

## Best Practices

- **Separate Environments**: Use different Argo CD projects for dev/staging/prod
- **Automated Testing**: Integrate with CI/CD for pre-deployment validation
- **Monitoring**: Set up alerts for sync failures
- **Documentation**: Keep deployment documentation in Git alongside manifests
- **Security**: Regular rotation of Argo CD admin credentials