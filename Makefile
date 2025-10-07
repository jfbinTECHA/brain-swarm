## 🧠 BrainSwarmOps Build Automation

SHELL := /bin/bash

.PHONY: build up down restart logs pdf-docs

build:
	@echo "🔨 Building BrainSwarmOps stack..."
	docker compose build

up:
	@echo "🚀 Starting BrainSwarmOps stack..."
	docker compose up -d

down:
	@echo "🛑 Stopping BrainSwarmOps stack..."
	docker compose down --remove-orphans

restart:
	@echo "🔁 Restarting BrainSwarmOps stack..."
	docker compose down --remove-orphans
	docker compose up -d --build

logs:
	@echo "📜 Showing logs for all containers..."
	docker compose logs -f --tail=50

pdf-docs:
	@echo "🧾 Generating all BrainSwarmOps PDF documentation..."
	python3 tools/generate_admin_console_pdf.py
	python3 tools/generate_production_deployment_pdf.py
	@echo "✅ All PDF docs rebuilt under ./docs/"