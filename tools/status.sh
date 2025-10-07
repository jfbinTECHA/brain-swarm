#!/usr/bin/env bash
echo "🌐 BrainSwarmOps Service Status:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
echo
curl -s localhost:8001/healthz | jq