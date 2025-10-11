#!/bin/bash

# Cortex AI Demo Script
# This script demonstrates the basic functionality of the Cortex AI stack

set -e

echo "🧠 Cortex AI Prototype Demo"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[DEMO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    error "Docker is not running. Please start Docker first."
    exit 1
fi

log "Starting Cortex AI stack..."
make up

# Wait for services to be ready
log "Waiting for services to be healthy..."
sleep 10

# Check service status
info "Checking service status:"
make status

# Test API endpoints
log "Testing API endpoints..."

# Ping endpoint
if curl -s http://localhost:8001/ping | grep -q "redis"; then
    log "✅ API ping successful"
else
    error "❌ API ping failed"
fi

# Metrics endpoint
if curl -s http://localhost:8001/metrics | grep -q "prometheus"; then
    log "✅ Metrics endpoint working"
else
    warn "⚠️  Metrics endpoint not accessible (may be normal if no requests made yet)"
fi

# Check Grafana
if curl -s -I http://localhost:3000 | grep -q "302"; then
    log "✅ Grafana responding (login page)"
else
    error "❌ Grafana not accessible"
fi

# Check Prometheus
if curl -s -I http://localhost:9090 | grep -q "200"; then
    log "✅ Prometheus responding"
else
    error "❌ Prometheus not accessible"
fi

log "Demo complete!"
info "Access your services:"
echo "  📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  🚀 API Docs: http://localhost:8001/docs"
echo "  ❤️  API Health: http://localhost:8001/ping"
echo ""
info "To stop the stack: make down"
info "To view logs: make logs"
info "To restart: make clean"