#!/bin/bash
# Production Deployment Script for Brain Swarm with Full Observability Stack
# Run with: chmod +x deploy-production.sh && ./deploy-production.sh

set -e

NAMESPACE="brainswarm"
HELM_CHART="./helm/brain-swarm"
VALUES_FILE="./helm/brain-swarm/values-production.yaml"

echo "🚀 Starting Brain Swarm Production Deployment..."

# Check prerequisites
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting."; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "❌ helm is required but not installed. Aborting."; exit 1; }

# Create namespace
echo "📁 Creating namespace: $NAMESPACE"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply secrets
echo "🔐 Applying secrets..."
kubectl apply -f k8s-secrets.yaml -n $NAMESPACE

# Wait for secrets to be ready
kubectl wait --for=condition=complete --timeout=60s job/secrets-setup -n $NAMESPACE 2>/dev/null || true

# Deploy with Helm
echo "⚓ Deploying Brain Swarm with Helm..."
helm upgrade --install brain-swarm $HELM_CHART \
  -f $VALUES_FILE \
  -n $NAMESPACE \
  --wait \
  --timeout=600s \
  --create-namespace

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/brain-swarm-api -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/brain-swarm-chroma -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/brain-swarm-swarmview -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/brain-swarm-swarmops-hook -n $NAMESPACE

# Check pod status
echo "📊 Pod Status:"
kubectl get pods -n $NAMESPACE

# Check service endpoints
echo "🌐 Service Endpoints:"
kubectl get svc -n $NAMESPACE

# Test key endpoints
echo "🧪 Testing endpoints..."

# Test API health
API_POD=$(kubectl get pods -l app.kubernetes.io/component=api -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
kubectl exec $API_POD -n $NAMESPACE -- curl -f http://localhost:8000/health || echo "⚠️  API health check failed"

# Test SwarmOps hook
HOOK_POD=$(kubectl get pods -l app.kubernetes.io/component=swarmops-hook -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
kubectl exec $HOOK_POD -n $NAMESPACE -- curl -f http://localhost:8080/health || echo "⚠️  SwarmOps hook health check failed"

# Display access information
echo ""
echo "✅ Brain Swarm Production Deployment Complete!"
echo ""
echo "🔗 Access URLs:"
echo "   API: https://brain-swarm.yourcompany.com"
echo "   Swarm View: https://brain-swarm.yourcompany.com/swarmview/"
echo "   Grafana: https://grafana.yourcompany.com/d/cortex-overview"
echo "   Prometheus: https://prometheus.yourcompany.com"
echo ""
echo "📊 Monitoring:"
echo "   kubectl port-forward svc/grafana 3000:3000 -n monitoring"
echo "   kubectl port-forward svc/prometheus 9090:9090 -n monitoring"
echo ""
echo "🔧 Troubleshooting:"
echo "   kubectl logs -l app.kubernetes.io/component=api -n $NAMESPACE"
echo "   kubectl describe pods -n $NAMESPACE"
echo ""
echo "🎯 Next Steps:"
echo "   1. Configure external DNS for ingress"
echo "   2. Set up SSL certificates with cert-manager"
echo "   3. Configure backup policies for persistent volumes"
echo "   4. Set up log aggregation (ELK/EFK stack)"
echo "   5. Configure horizontal pod autoscaling"