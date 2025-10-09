#!/usr/bin/env bash
# 🧠 BrainSwarm Quickstart Launcher
# Starts backend (FastAPI), frontend (Zeta/Kilo), and dashboards in one command

set -e

echo "🚀 BrainSwarm Quickstart Initializing..."

# --- 1. Start backend (FastAPI) ---
if ! pgrep -f "uvicorn.*brainswarm.main" >/dev/null; then
  echo "🧠 Starting BrainSwarm API..."
  cd /home/sysop/brainswarm
  nohup /home/sysop/brainswarm/venv/bin/python -m uvicorn brainswarm.main:app --host 0.0.0.0 --port 8001 > /home/sysop/brainswarm_api.log 2>&1 &
else
  echo "✅ BrainSwarm API already running."
fi

# --- 2. Start frontend (Zeta/Kilo) ---
if ! pgrep -f "next dev" >/dev/null; then
  echo "🖥️  Launching Zeta/Kilo Dashboard..."
  cd /home/sysop/zetav10
  if command -v pnpm >/dev/null 2>&1; then
    nohup pnpm dev > /home/sysop/zetav10.log 2>&1 &
  elif command -v npm >/dev/null 2>&1; then
    nohup npm run dev > /home/sysop/zetav10.log 2>&1 &
  else
    echo "⚠️  pnpm/npm not found — install Node 20+ with pnpm or npm."
  fi
else
  echo "✅ Zeta/Kilo Dashboard already running."
fi

# --- 3. Optional Prometheus + Grafana ---
if [ -f /home/sysop/brainswarm-compose.yml ]; then
  echo "📊 Starting Prometheus + Grafana stack..."
  cd /home/sysop
  docker compose -f brainswarm-compose.yml up -d
else
  echo "ℹ️  No brainswarm-compose.yml found; skipping metrics stack."
fi

# --- 4. Wait and open dashboards ---
sleep 5

open_url() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$url" >/dev/null 2>&1 || true
  else
    echo "→ Open manually: $url"
  fi
}

echo "🌐 Opening dashboards..."
open_url "http://localhost:3000/dashboard"
open_url "http://localhost:9090"
open_url "http://localhost:3000"

echo ""
echo "✅ All systems launched:"
echo "   • Backend (FastAPI):    http://localhost:8001"
echo "   • Dashboard (Kilo UI):  http://localhost:3000/dashboard"
echo "   • Prometheus:           http://localhost:9090"
echo "   • Grafana:              http://localhost:3000 (if enabled)"
echo ""
echo "📜 Logs: tail -f ~/brainswarm_api.log ~/zetav10.log"
echo ""
echo "🛑 Stop all services with:  make stop"