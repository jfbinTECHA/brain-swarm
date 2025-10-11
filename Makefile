.PHONY: up down status logs clean test build restart

# Default target
help:
	@echo "Available targets:"
	@echo "  up       - Start all services"
	@echo "  down     - Stop all services"
	@echo "  status   - Show service status"
	@echo "  logs     - Follow service logs"
	@echo "  clean    - Remove containers and volumes"
	@echo "  build    - Rebuild all services"
	@echo "  restart  - Restart all services"
	@echo "  test     - Run basic health checks"

# Start services
up:
	cd infra && docker compose up -d
	@echo "Services started. Access:"
	@echo "  Grafana: http://localhost:3000"
	@echo "  API: http://localhost:8001/ping"
	@echo "  Prometheus: http://localhost:9090"

# Stop services
down:
	cd infra && docker compose down

# Show status
status:
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Health checks:"
	@curl -s http://localhost:8001/ping | grep -q 'redis' && echo "✅ API healthy" || echo "❌ API not responding"
	@curl -s -I http://localhost:9090 | grep -q '200 OK' && echo "✅ Prometheus up" || echo "❌ Prometheus down"
	@curl -s -I http://localhost:3000 | grep -q '302 Found' && echo "✅ Grafana responding" || echo "❌ Grafana down"

# Follow logs
logs:
	cd infra && docker compose logs -f

# Clean rebuild
clean:
	cd infra && docker compose down -v --remove-orphans
	cd infra && docker compose up -d --build

# Build services
build:
	cd infra && docker compose build

# Restart services
restart:
	cd infra && docker compose restart

# Basic tests
test:
	@echo "Running health checks..."
	@curl -s http://localhost:8001/ping > /dev/null && echo "✅ API reachable" || echo "❌ API unreachable"
	@curl -s http://localhost:9090/-/healthy > /dev/null && echo "✅ Prometheus healthy" || echo "❌ Prometheus unhealthy"
	@curl -s -I http://localhost:3000 | grep -q 'HTTP' && echo "✅ Grafana reachable" || echo "❌ Grafana unreachable"