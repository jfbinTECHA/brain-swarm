.PHONY: help up down status logs clean test build restart lint sbom metrics

# Default target
help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Start services
up:  ## Start docker stack
	docker compose -f infra/docker-compose.yml up -d
	@echo "Services started. Access:"
	@echo "  Grafana: http://localhost:3000"
	@echo "  API: http://localhost:8001/docs"
	@echo "  Prometheus: http://localhost:9090"

# Stop services
down:  ## Stop stack
	docker compose -f infra/docker-compose.yml down

# Show status
status:  ## Check service health
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Health checks:"
	@curl -s http://localhost:8001/ping | grep -q 'redis' && echo "✅ API healthy" || echo "❌ API not responding"
	@curl -s -I http://localhost:9090 | grep -q '200 OK' && echo "✅ Prometheus up" || echo "❌ Prometheus unreachable"
	@curl -s -I http://localhost:3000 | grep -q '302 Found' && echo "✅ Grafana responding" || echo "❌ Grafana down or blocked"

# Follow logs
logs:  ## Follow service logs
	docker compose -f infra/docker-compose.yml logs -f

# Clean rebuild
clean:  ## Remove containers and volumes, rebuild
	docker compose -f infra/docker-compose.yml down -v --remove-orphans
	docker compose -f infra/docker-compose.yml up -d --build

# Build services
build:  ## Build docker images
	docker compose -f infra/docker-compose.yml build

# Restart services
restart:  ## Restart all services
	docker compose -f infra/docker-compose.yml restart

# Run tests
test:  ## Run test suite
	pytest -v

# Lint code
lint:  ## Lint Python code
	ruff check .

# Security scan
sbom:  ## Generate SBOM and security scan
	trivy fs .

# Fix code style
fix:  ## Auto-fix code style issues
	ruff check . --fix && black . && isort .

# Developer metrics
metrics:  ## Show aggregated developer metrics
	@echo "=== Redis Stats ==="
	@docker exec brain-swarm-redis redis-cli info stats 2>/dev/null | grep -E "(total_connections_received|total_commands_processed|used_memory|keyspace_hits|keyspace_misses)" || echo "Redis not running"
	@echo ""
	@echo "=== FastAPI Metrics ==="
	@curl -s http://localhost:8001/metrics 2>/dev/null | grep -E "(http_requests_total|fastapi_requests_total)" | head -5 || echo "FastAPI metrics not available"
	@echo ""
	@echo "=== Prometheus Targets ==="
	@curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets[] | select(.health == "up") | "\(.labels.job): \(.health)"' 2>/dev/null | sort | uniq || echo "Prometheus not accessible"