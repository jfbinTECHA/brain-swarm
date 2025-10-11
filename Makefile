.PHONY: help up down status logs clean test build restart lint sbom

# Default target
help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Start services
up:  ## Start docker stack
	cd infra && docker compose up -d
	@echo "Services started. Access:"
	@echo "  Grafana: http://localhost:3000"
	@echo "  API: http://localhost:8001/docs"
	@echo "  Prometheus: http://localhost:9090"

# Stop services
down:  ## Stop stack
	cd infra && docker compose down

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
	cd infra && docker compose logs -f

# Clean rebuild
clean:  ## Remove containers and volumes, rebuild
	cd infra && docker compose down -v --remove-orphans
	cd infra && docker compose up -d --build

# Build services
build:  ## Build docker images
	cd infra && docker compose build

# Restart services
restart:  ## Restart all services
	cd infra && docker compose restart

# Run tests
test:  ## Run test suite
	pytest tests/ -v

# Lint code
lint:  ## Lint Python code
	ruff check backend/
	ruff format --check backend/

# Security scan
sbom:  ## Generate SBOM and security scan
	trivy fs --format table --output trivy-report.md .