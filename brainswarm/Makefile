# 🧠 BrainSwarmOps Makefile
# Quick utility targets for local developer startup and ops tasks

.PHONY: quickstart logs stop

quickstart:
	@echo "🚀 Launching BrainSwarm full stack..."
	@bash ops/brainswarm-quickstart.sh

logs:
	@echo "📜 Showing backend + frontend logs..."
	@tail -n 40 -f ~/brainswarm_api.log ~/zetav10.log

stop:
	@echo "🛑 Stopping BrainSwarm services..."
	@pkill -f "uvicorn.*brainswarm.main" || true
	@pkill -f "next dev" || true
	@docker compose -f ~/brainswarm-compose.yml down || true

help:
	@echo ""
	@echo "BrainSwarmOps Commands:"
	@echo "  make quickstart   – Run backend, frontend, and dashboards"
	@echo "  make logs         – Tail logs for backend & frontend"
	@echo "  make stop         – Stop all running BrainSwarm processes"
	@echo ""