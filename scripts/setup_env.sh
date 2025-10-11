#!/usr/bin/env bash
set -e

echo "🧠  Brain-Swarm Local Setup Utility"
echo "----------------------------------"

# --- Prerequisite checks -----------------------------------------------------
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 not found"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git not found"; exit 1; }

echo "✅ Environment detected:"
python3 --version
docker --version
git --version
echo

# --- Create virtual environment ----------------------------------------------
if [ ! -d ".venv" ]; then
  echo "⚙️  Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "✅ Virtual environment activated"

# --- Install dependencies -----------------------------------------------------
REQ_FILES=(
  "requirements.txt"
  "requirements-bridge.txt"
  "requirements-cortex.txt"
  "requirements-dev.txt"
)

for req in "${REQ_FILES[@]}"; do
  if [ -f "$req" ]; then
    echo "📦 Installing dependencies from $req..."
    pip install -r "$req" >/dev/null
  fi
done

echo "✅ All dependencies installed"
echo

# --- Verify core libraries ----------------------------------------------------
python - <<'EOF'
import sys
try:
    import fastapi, redis, duckdb, chromadb
    print("✅ Core libraries verified: FastAPI, Redis, DuckDB, ChromaDB")
except Exception as e:
    print("⚠️  Library check failed:", e)
    sys.exit(1)
EOF

# --- Launch Docker stack ------------------------------------------------------
if [ -f "Makefile" ]; then
  echo "🚀 Starting Docker stack via Makefile..."
  make up
else
  echo "⚠️  No Makefile found; starting docker-compose manually..."
  docker compose up -d
fi

echo
echo "✅ Containers running:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# --- Summary -----------------------------------------------------------------
echo
echo "✨ Brain-Swarm local environment ready!"
echo "Access points:"
echo "  - API Docs:     http://localhost:8001/docs"
echo "  - Metrics:      http://localhost:8001/metrics"
echo "  - Grafana:      http://localhost:3000"
echo "  - Prometheus:   http://localhost:9090"
echo
echo "To stop containers: make down"
echo "To deactivate venv: deactivate"
echo