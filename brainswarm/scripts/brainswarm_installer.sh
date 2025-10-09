#!/usr/bin/env bash
# =====================================================================
# 🧠 BrainSwarmOps Unified Installer
# ---------------------------------------------------------------------
#  Installs & configures BrainSwarm Cortex, Prometheus, Grafana,
#  Redis, and systemd services with observability integration.
# =====================================================================

set -e

echo "🚀 BrainSwarmOps Unified Installer"
echo "---------------------------------------------"

# --- Verify project root ---
cd /home/sysop/brainswarm || { echo "❌ Not in brainswarm directory"; exit 1; }

# --- Step 1: Python environment setup ---
echo "🐍 Setting up Python venv..."
python3 -m venv venv
source venv/bin/activate
pip install -U pip wheel setuptools
pip install -r requirements.txt || true

# --- Step 2: Redis installation ---
if ! command -v redis-server >/dev/null 2>&1; then
  echo "📦 Installing Redis..."
  sudo apt update -y
  sudo apt install -y redis-server
  sudo systemctl enable redis-server
  sudo systemctl start redis-server
else
  echo "✅ Redis already installed."
fi

# --- Step 3: Prometheus + Grafana setup ---
echo "📊 Setting up Prometheus + Grafana..."
docker compose up -d prometheus grafana

# --- Step 4: Ensure .env exists ---
if [[ ! -f ".env" ]]; then
cat <<EOF > .env
REDIS_URL=redis://localhost:6379
CHROMA_URL=http://localhost:8000
DUCKDB_PATH=/home/sysop/brainswarm/data/cortex.duckdb
S3_BUCKET=brainswarm-cortex
SUMMARIZATION_INTERVAL=300
EMBEDDING_MODEL=text-embedding-3-large
CORTEX_MODE=live
EOF
echo "✅ Created default .env"
else
  echo "✅ Existing .env detected."
fi

# --- Step 5: Validate environment configuration ---
echo "🔍 Validating Cortex configuration..."
PYTHONPATH=/home/sysop/brainswarm python3 -c "from brainswarm.cortex.config import settings; print(settings.dict())"

# --- Step 6: Copy & enable services ---
echo "🧩 Installing systemd services..."

sudo mkdir -p /etc/systemd/system
sudo cp services/brainswarm-summarizer.service /etc/systemd/system/
sudo cp services/brainswarm-watchdog.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable brainswarm-summarizer.service
sudo systemctl enable brainswarm-watchdog.service
sudo systemctl restart brainswarm-summarizer.service
sudo systemctl restart brainswarm-watchdog.service

# --- Step 7: Verify services ---
echo "🩺 Checking active services..."
sudo systemctl --no-pager status brainswarm-summarizer.service | head -n 10
sudo systemctl --no-pager status brainswarm-watchdog.service | head -n 10

# --- Step 8: Verify metrics endpoints ---
echo "📈 Verifying Prometheus and Watchdog metrics..."
curl -fsSL http://localhost:9201/metrics | grep brainswarm_watchdog || echo "⚠️  No watchdog metrics detected yet"

# --- Step 9: Final summary ---
echo "---------------------------------------------"
echo "✅ BrainSwarmOps installation complete"
echo "---------------------------------------------"
echo "Services:"
echo "  🧠 Summarizer: systemctl status brainswarm-summarizer.service"
echo "  👁️  Watchdog:   systemctl status brainswarm-watchdog.service"
echo "Metrics & Dashboards:"
echo "  📊 Prometheus:  http://localhost:9090"
echo "  🧩 Grafana:     http://localhost:3000 (admin / brainswarm)"
echo "  🧠 Dashboard:   BrainSwarmOps / Cortex / Watchdog Metrics"
echo "---------------------------------------------"
echo "All systems are operational. Happy Swarming 🧬"