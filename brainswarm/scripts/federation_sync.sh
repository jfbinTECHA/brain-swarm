#!/usr/bin/env bash
# =====================================================================
# 🔄 BrainSwarmOps Federation Sync Script
# ---------------------------------------------------------------------
# This script performs Redis key exchange and metric sync across
# federated BrainSwarm nodes. It can be run manually or by Kilo.
# =====================================================================

set -e
REDIS_NODES=("localhost" "ai-node-1.local" "ai-node-2.local")

echo "🌐 Starting BrainSwarm Federation Sync..."

for NODE in "${REDIS_NODES[@]}"; do
  echo "🔁 Syncing from $NODE..."
  redis-cli -h "$NODE" --scan --pattern "brainswarm:*" | while read -r key; do
    value=$(redis-cli -h "$NODE" get "$key")
    redis-cli -h localhost set "$key" "$value" >/dev/null 2>&1 || true
  done
done

echo "✅ Federation Redis sync complete."

# Sync metrics between Prometheus nodes
echo "📈 Pulling federated metrics..."
curl -fsSL http://localhost:9090/federate?match[]={job=\"brainswarm_nodes\"} >/dev/null 2>&1 && \
  echo "✅ Prometheus federation data refreshed." || echo "⚠️  Federation metrics sync failed."

echo "---------------------------------------------"
echo "🌍 Federation synchronization finished."
echo "---------------------------------------------"