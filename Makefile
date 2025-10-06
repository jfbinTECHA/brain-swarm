SHELL := /bin/bash

APP ?= brain-swarm
NAMESPACE ?= brainswarm
CHART_DIR := helm/brain-swarm
DEV_VALUES := $(CHART_DIR)/values-dev.yaml
PROD_VALUES := $(CHART_DIR)/values-prod.yaml

IMG_BRIDGE ?= jfbintecha/swarmops-hook
IMG_CORTEX ?= jfbintecha/knowledge-cortex
TAG ?= $(shell git rev-parse --short HEAD)

.PHONY: help
help:
	@echo "Brain Swarm Ops - Deployment & Compliance"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build        Build Docker images"
	@echo "  push         Push images to registry"
	@echo "  dev-up       Deploy to development"
	@echo "  prod-up      Deploy to production"
	@echo "  dev-down     Remove development deployment"
	@echo ""
	@echo "Security & Compliance:"
	@echo "  sbom         Generate Software Bill of Materials"
	@echo "  scan         Vulnerability scanning"
	@echo ""
	@echo "Development:"
	@echo "  render       Render Helm templates"
	@echo "  docs         Build documentation"
	@echo "  deploy-docs  Deploy documentation to GitHub Pages"
	@echo ""
	@echo "Combined workflows:"
	@echo "  make build sbom scan    - Build, generate SBOMs, and scan"
	@echo "  make push prod-up       - Push images and deploy to prod"

.PHONY: build
build:
	docker build -t $(IMG_BRIDGE):$(TAG) -f Dockerfile.bridge .
	docker build -t $(IMG_CORTEX):$(TAG) -f Dockerfile.cortex .

.PHONY: push
push:
	docker push $(IMG_BRIDGE):$(TAG)
	docker push $(IMG_CORTEX):$(TAG)

.PHONY: dev-up
dev-up:
	helm upgrade --install $(APP) $(CHART_DIR) -n $(NAMESPACE) --create-namespace -f $(DEV_VALUES) \
		--set bridge.image=$(IMG_BRIDGE):$(TAG) \
		--set cortex.image=$(IMG_CORTEX):$(TAG)

.PHONY: dev-down
dev-down:
	helm uninstall $(APP) -n $(NAMESPACE) || true

.PHONY: prod-up
prod-up:
	helm upgrade --install $(APP) $(CHART_DIR) -n $(NAMESPACE) -f $(PROD_VALUES)

.PHONY: render
render:
	helm template $(APP) $(CHART_DIR) -f $(DEV_VALUES) > /tmp/$(APP)-manifest.yaml
	@echo "Rendered to /tmp/$(APP)-manifest.yaml"

.PHONY: docs
docs:
	mkdocs build

.PHONY: deploy-docs
deploy-docs:
	mkdocs gh-deploy --force

# Supply-chain security: SBOM generation and vulnerability scanning
.PHONY: sbom
sbom:
	@echo "🔍 Generating SBOMs with Syft..."
	syft $(IMG_BRIDGE):$(TAG) -o spdx-json > sbom-bridge-$(TAG).spdx.json
	syft $(IMG_CORTEX):$(TAG) -o spdx-json > sbom-cortex-$(TAG).spdx.json
	@echo "✅ SBOMs generated: sbom-bridge-$(TAG).spdx.json, sbom-cortex-$(TAG).spdx.json"

.PHONY: scan
scan:
	@echo "🔍 Scanning for vulnerabilities with Grype..."
	grype $(IMG_BRIDGE):$(TAG) --output sarif > scan-bridge-$(TAG).sarif
	grype $(IMG_CORTEX):$(TAG) --output sarif > scan-cortex-$(TAG).sarif
	@echo "✅ Vulnerability scans completed: scan-bridge-$(TAG).sarif, scan-cortex-$(TAG).sarif"