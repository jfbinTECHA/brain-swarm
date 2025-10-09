# Open Policy Agent (OPA) / Gatekeeper Policies

This directory contains OPA/Gatekeeper constraint templates and constraints to enforce security and operational best practices for the Brain Swarm Ops platform.

## Policies Included

### 1. HTTPS Only (`constraint-template-tls.yaml`)
- **Purpose**: Ensures all Ingress resources use HTTPS/TLS
- **Enforcement**: Blocks Ingress creation without TLS configuration
- **Scope**: `brainswarm` namespace

### 2. Non-Root Containers (`constraint-template-nonroot.yaml`)
- **Purpose**: Prevents containers from running as root user
- **Enforcement**: Requires `runAsUser` to be set to non-zero value
- **Scope**: All pods in `brainswarm` namespace

### 3. Resource Limits (`constraint-template-resourcelimits.yaml`)
- **Purpose**: Ensures containers have proper resource limits and requests
- **Enforcement**: Requires CPU/memory limits and requests for all containers
- **Scope**: All pods in `brainswarm` namespace

## Installation

### Prerequisites
- Open Policy Agent (OPA) Gatekeeper installed in cluster
- `kubectl` access with cluster-admin privileges

### Deploy Policies
```bash
# Install all constraint templates and constraints
kubectl apply -f policies/

# Verify installation
kubectl get constrainttemplates
kubectl get constraints
```

## Usage

### Testing Policies
```bash
# Try to create a pod without resource limits (should be blocked)
kubectl apply -f test-pod-without-limits.yaml

# Check policy violations
kubectl get constraintspodstatus
```

### Audit Mode (Monitoring Only)
To run policies in audit mode instead of enforcement:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sContainerResourceLimits
metadata:
  name: containers-must-have-limits
spec:
  enforcementAction: warn  # Change from 'deny' to 'warn'
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

## Policy Violations

### Common Violations and Fixes

#### HTTPS Violation
```
Violation: Ingress must use HTTPS (TLS configuration required)
```
**Fix**: Add TLS configuration to Ingress:
```yaml
spec:
  tls:
    - hosts:
        - your-domain.com
      secretName: tls-secret
```

#### Non-Root Violation
```
Violation: Container 'app' must not run as root
```
**Fix**: Set non-root user in deployment:
```yaml
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
  containers:
    - name: app
      securityContext:
        runAsNonRoot: true
```

#### Resource Limits Violation
```
Violation: Container 'app' must have resource limits set
```
**Fix**: Add resource limits to deployment:
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

## Monitoring

### Check Policy Status
```bash
# View constraint templates
kubectl get constrainttemplates

# View active constraints
kubectl get constraints

# Check audit results
kubectl get constraintspodstatus
```

### Logs
```bash
# Gatekeeper controller logs
kubectl logs -n gatekeeper-system deployment/gatekeeper-controller-manager
```

## Customization

### Adding New Policies
1. Create new `constraint-template-*.yaml` file
2. Define Rego policy logic
3. Create corresponding constraint
4. Test thoroughly before production deployment

### Namespace-Specific Policies
Modify the `match.namespaces` field in constraints:
```yaml
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
      - staging
```

## Troubleshooting

### Policy Not Working
1. Check Gatekeeper installation: `kubectl get pods -n gatekeeper-system`
2. Verify constraint template: `kubectl describe constrainttemplate <name>`
3. Check constraint status: `kubectl describe constraint <name>`

### False Positives
- Review Rego logic in constraint template
- Check namespace exclusions
- Verify resource labels/selectors

## Security Benefits

- **Zero-Trust Networking**: HTTPS-only ingress
- **Container Security**: Non-root execution prevents privilege escalation
- **Resource Protection**: Limits prevent resource exhaustion attacks
- **Compliance**: Enforces enterprise security standards
- **Audit Trail**: All policy violations are logged

## Integration with CI/CD

Add policy validation to your CI/CD pipeline:

```bash
# Validate against policies before deployment
kubectl apply --dry-run=server -f deployment.yaml