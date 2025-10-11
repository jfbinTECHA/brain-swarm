# 🔧 Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Helm Chart Installation Fails

**Symptoms:**
- `helm install` command fails
- Error messages about missing dependencies
- Kubernetes API errors

**Solutions:**

1. **Check Kubernetes Version Compatibility**
   ```bash
   kubectl version --short
   ```
   Ensure you're running Kubernetes 1.24+.

2. **Verify Helm Version**
   ```bash
   helm version
   ```
   Ensure you're using Helm 3.8+.

3. **Check Namespace Creation**
   ```bash
   kubectl create namespace brainswarm --dry-run=client
   ```
   Ensure you have permissions to create namespaces.

4. **Validate Prerequisites**
   ```bash
   # Check if ingress controller is installed
   kubectl get pods -n ingress-nginx

   # Check if Redis is available
   kubectl get svc redis -n brainswarm
   ```

#### Pod Startup Failures

**Symptoms:**
- Pods stuck in `Pending` or `CrashLoopBackOff` state
- Image pull errors
- Resource constraint errors

**Solutions:**

1. **Check Pod Status**
   ```bash
   kubectl get pods -n brainswarm
   kubectl describe pod <pod-name> -n brainswarm
   ```

2. **Examine Pod Logs**
   ```bash
   kubectl logs <pod-name> -n brainswarm --previous
   ```

3. **Check Resource Availability**
   ```bash
   kubectl describe nodes
   # Look for insufficient CPU/memory
   ```

4. **Verify Image Pull**
   ```bash
   kubectl describe pod <pod-name> -n brainswarm | grep -A 10 "Containers"
   ```

### Webhook Issues

#### Webhooks Not Triggering

**Symptoms:**
- No incidents created from webhook calls
- HTTP 403 Forbidden responses
- Rate limiting errors

**Solutions:**

1. **Verify Ingress Configuration**
   ```bash
   kubectl describe ingress brain-swarm-ticket-bridge -n brainswarm
   ```

2. **Check IP Whitelisting**
   ```bash
   # Test from allowed IP
   curl -I https://webhooks.brainswarm.ai/gh-webhook

   # Check ingress controller logs
   kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
   ```

3. **Validate Webhook Payload**
   ```bash
   # Test with valid payload
   curl -X POST https://webhooks.brainswarm.ai/gh-webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "webhook"}'
   ```

4. **Check Rate Limiting**
   ```bash
   # Monitor rate limit headers
   curl -I https://webhooks.brainswarm.ai/gh-webhook
   # Look for X-RateLimit-* headers
   ```

#### Invalid Webhook Signatures

**Symptoms:**
- Webhooks accepted but not processed
- Authentication errors in logs

**Solutions:**

1. **Verify GitHub Webhook Secret**
   ```bash
   # Check if secret is configured
   kubectl get secret brain-swarm-webhook-secrets -n brainswarm
   ```

2. **Validate Signature Calculation**
   ```bash
   # Test signature manually
   echo -n '{"test":"data"}' | openssl dgst -sha256 -hmac "your-secret" -binary | base64
   ```

#### Ticket Creation Failures

**Symptoms:**
- Webhooks accepted but no tickets created
- External API errors in logs

**Solutions:**

1. **Check External API Credentials**
   ```bash
   kubectl get secret brain-swarm-webhook-secrets -n brainswarm -o yaml
   ```

2. **Verify API Permissions**
   ```bash
   # Test Jira API access
   curl -u user:token https://your-jira.atlassian.net/rest/api/3/project

   # Test GitHub API access
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```

3. **Check Network Connectivity**
   ```bash
   # From pod
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- curl -I https://api.github.com
   ```

### AI Processing Issues

#### AI Triage Not Working

**Symptoms:**
- Incidents created but no AI analysis
- AI confidence scores missing
- Processing timeouts

**Solutions:**

1. **Check AI Service Health**
   ```bash
   kubectl get pods -n brainswarm | grep api
   kubectl logs deployment/brain-swarm-api -n brainswarm
   ```

2. **Verify AI API Connectivity**
   ```bash
   # Test internal API call
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     curl http://brain-swarm-api.brainswarm.svc.cluster.local:8000/health
   ```

3. **Check AI Processing Logs**
   ```bash
   kubectl logs deployment/brain-swarm-ticket-bridge -n brainswarm | grep -i ai
   ```

#### Low AI Confidence Scores

**Symptoms:**
- AI analysis shows low confidence (<50%)
- Incorrect incident classification

**Solutions:**

1. **Check Training Data Quality**
   ```bash
   # Verify historical incident data
   kubectl exec -it deployment/brain-swarm-api -n brainswarm -- \
     python -c "from cortex.training import check_training_data; check_training_data()"
   ```

2. **Update AI Models**
   ```bash
   # Trigger model retraining
   curl -X POST https://api.brainswarm.ai/training/replay-incidents \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"source": "github", "days_back": 30}'
   ```

### Monitoring Issues

#### Metrics Not Appearing

**Symptoms:**
- Prometheus shows no BrainSwarmOps metrics
- Grafana dashboards are empty

**Solutions:**

1. **Check Service Discovery**
   ```bash
   # Verify ServiceMonitor
   kubectl get servicemonitor -n brainswarm

   # Check Prometheus targets
   kubectl port-forward svc/prometheus 9090:9090 -n monitoring
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.service == "brain-swarm")'
   ```

2. **Validate Metrics Exposure**
   ```bash
   # Check metrics endpoint
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     curl http://localhost:8080/metrics | head -20
   ```

3. **Verify Prometheus Configuration**
   ```bash
   kubectl get configmap prometheus-config -n monitoring -o yaml
   ```

#### Grafana Dashboard Issues

**Symptoms:**
- Dashboards not loading
- Data source connection errors

**Solutions:**

1. **Check Grafana Data Source**
   ```bash
   # Access Grafana
   kubectl port-forward svc/grafana 3000:3000 -n monitoring
   # Go to Configuration → Data Sources → Prometheus
   ```

2. **Verify Dashboard Import**
   ```bash
   kubectl get configmap brain-swarm-grafana-dashboards -n brainswarm
   ```

3. **Check Grafana Logs**
   ```bash
   kubectl logs deployment/grafana -n brainswarm
   ```

### Performance Issues

#### High Latency

**Symptoms:**
- Webhook response times >5 seconds
- AI processing timeouts

**Solutions:**

1. **Check Resource Utilization**
   ```bash
   kubectl top pods -n brainswarm
   kubectl describe nodes
   ```

2. **Scale Components**
   ```bash
   # Scale ticket bridge
   kubectl scale deployment brain-swarm-ticket-bridge --replicas=3 -n brainswarm

   # Scale API
   kubectl scale deployment brain-swarm-api --replicas=3 -n brainswarm
   ```

3. **Optimize Database Queries**
   ```bash
   # Check slow queries
   kubectl logs deployment/brain-swarm-api -n brainswarm | grep -i slow
   ```

#### Memory Issues

**Symptoms:**
- OOMKilled pods
- Memory usage spikes

**Solutions:**

1. **Increase Memory Limits**
   ```bash
   kubectl patch deployment brain-swarm-ticket-bridge -n brainswarm \
     --type='json' \
     -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"}]'
   ```

2. **Check Memory Leaks**
   ```bash
   # Monitor memory usage
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
   ```

3. **Enable Memory Profiling**
   ```bash
   # Add memory profiling
   kubectl set env deployment/brain-swarm-api MEMORY_PROFILING=enabled -n brainswarm
   ```

### Security Issues

#### Authentication Failures

**Symptoms:**
- 401 Unauthorized errors
- Token validation failures

**Solutions:**

1. **Check JWT Configuration**
   ```bash
   kubectl get secret brain-swarm-secrets -n brainswarm -o yaml
   ```

2. **Verify Token Expiration**
   ```bash
   # Decode JWT token
   echo "your.jwt.token" | jq -R 'split(".") | .[1] | @base64d | fromjson'
   ```

3. **Check Clock Synchronization**
   ```bash
   # Verify NTP sync
   kubectl exec -it deployment/brain-swarm-api -n brainswarm -- date
   ```

#### TLS Certificate Issues

**Symptoms:**
- HTTPS connection failures
- Certificate validation errors

**Solutions:**

1. **Check Certificate Status**
   ```bash
   kubectl get certificate -n brainswarm
   kubectl describe certificate brain-swarm-tls -n brainswarm
   ```

2. **Verify Certificate Chain**
   ```bash
   # Test certificate
   openssl s_client -connect webhooks.brainswarm.ai:443 -servername webhooks.brainswarm.ai
   ```

3. **Renew Certificates**
   ```bash
   kubectl delete certificate brain-swarm-tls -n brainswarm
   # Certificate will be re-issued automatically
   ```

### Network Issues

#### Service Discovery Problems

**Symptoms:**
- Inter-service communication failures
- DNS resolution errors

**Solutions:**

1. **Check DNS Resolution**
   ```bash
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     nslookup brain-swarm-api.brainswarm.svc.cluster.local
   ```

2. **Verify Service Endpoints**
   ```bash
   kubectl get endpoints -n brainswarm
   ```

3. **Check Network Policies**
   ```bash
   kubectl get networkpolicy -n brainswarm
   ```

#### External API Connectivity

**Symptoms:**
- External service integration failures
- Timeout errors

**Solutions:**

1. **Test External Connectivity**
   ```bash
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     curl -I https://api.github.com
   ```

2. **Check Proxy Configuration**
   ```bash
   # Verify proxy settings
   kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- \
     env | grep -i proxy
   ```

3. **Validate Firewall Rules**
   ```bash
   # Check egress rules
   kubectl get networkpolicy -n brainswarm
   ```

## Diagnostic Tools

### Health Check Script

```bash
#!/bin/bash
# Comprehensive health check script

echo "🔍 BrainSwarmOps Health Check"
echo "================================"

# Check Kubernetes resources
echo "📋 Kubernetes Resources:"
kubectl get pods,svc,ingress -n brainswarm --no-headers | wc -l
echo "Expected: 6+ resources"

# Check webhook endpoints
echo "🔗 Webhook Endpoints:"
curl -s -o /dev/null -w "%{http_code}" https://webhooks.brainswarm.ai/gh-webhook
echo "Expected: 200"

# Check API health
echo "🏥 API Health:"
kubectl exec -it deployment/brain-swarm-api -n brainswarm -- curl -s http://localhost:8000/health | jq .status
echo "Expected: healthy"

# Check metrics
echo "📊 Metrics Collection:"
kubectl exec -it deployment/brain-swarm-ticket-bridge -n brainswarm -- curl -s http://localhost:8080/metrics | grep -c cortex_incident
echo "Expected: >0 metrics"

# Check AI processing
echo "🤖 AI Processing:"
kubectl logs deployment/brain-swarm-ticket-bridge -n brainswarm --tail=10 | grep -c "AI analysis"
echo "Expected: Recent AI activity"

echo "================================"
echo "✅ Health check complete"
```

### Log Analysis Script

```bash
#!/bin/bash
# Log analysis script

echo "📝 Log Analysis Report"
echo "======================"

# Error analysis
echo "❌ Error Summary:"
kubectl logs --all-containers --tail=1000 -n brainswarm | grep -i error | wc -l
echo "errors in recent logs"

# Performance analysis
echo "⚡ Performance Metrics:"
kubectl logs deployment/brain-swarm-ticket-bridge -n brainswarm --tail=100 | grep -o '"response_time":[0-9.]*' | awk -F: '{sum+=$2; count++} END {print "Average response time:", sum/count, "seconds"}'

# Incident processing
echo "🎯 Incident Processing:"
kubectl logs deployment/brain-swarm-ticket-bridge -n brainswarm --tail=100 | grep -c "Ticket created"
echo "tickets created recently"

echo "======================"
```

### Performance Benchmarking

```bash
#!/bin/bash
# Performance benchmarking script

echo "🏃 Performance Benchmark"
echo "========================"

# Webhook throughput test
echo "📨 Webhook Throughput:"
start_time=$(date +%s)
for i in {1..100}; do
  curl -s -X POST https://webhooks.brainswarm.ai/gh-webhook \
    -H "Content-Type: application/json" \
    -d '{"test": "benchmark"}' &
done
wait
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "100 requests in $duration seconds"
echo "Throughput: $((100/duration)) req/sec"

# Memory usage
echo "💾 Memory Usage:"
kubectl top pods -n brainswarm

# CPU usage
echo "🔥 CPU Usage:"
kubectl top pods -n brainswarm

echo "======================"
```

## Emergency Procedures

### System Recovery

1. **Scale Down Problematic Components**
   ```bash
   kubectl scale deployment brain-swarm-ticket-bridge --replicas=0 -n brainswarm
   ```

2. **Restart Services**
   ```bash
   kubectl rollout restart deployment/brain-swarm-ticket-bridge -n brainswarm
   ```

3. **Clear Queues**
   ```bash
   kubectl exec -it deployment/redis-master-0 -n brainswarm -- redis-cli FLUSHALL
   ```

### Data Recovery

1. **Backup Current State**
   ```bash
   # Backup configurations
   kubectl get configmap,secret -n brainswarm -o yaml > backup-$(date +%Y%m%d).yaml
   ```

2. **Restore from Backup**
   ```bash
   kubectl apply -f backup-20231005.yaml
   ```

### Escalation Contacts

- **Development Team**: dev@brainswarm.ai
- **Infrastructure Team**: infra@brainswarm.ai
- **Security Team**: security@brainswarm.ai
- **Management**: emergency@brainswarm.ai

## Prevention Best Practices

### Monitoring Setup
- Set up comprehensive alerting on all metrics
- Configure log aggregation and analysis
- Implement automated health checks

### Capacity Planning
- Monitor resource usage trends
- Plan for seasonal traffic increases
- Implement auto-scaling policies

### Backup Strategy
- Regular configuration backups
- Database backups for Cortex data
- Disaster recovery testing

### Security Hardening
- Regular security updates
- Access review and rotation
- Network policy enforcement

This troubleshooting guide provides comprehensive solutions for common BrainSwarmOps issues. For additional support, please refer to the [GitHub repository](https://github.com/brain-swarm/brain-swarm-ops) or contact the development team.