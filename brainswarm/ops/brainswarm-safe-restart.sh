#!/usr/bin/env bash
# ───────────────────────────────────────────────────────────────
# 🧠 BrainSwarm Safe Restart Script
# Handles port conflicts, DuckDB lock cleanup, and relaunches API.
# Location: /home/sysop/brainswarm/ops/brainswarm-safe-restart.sh
# Usage: ./ops/brainswarm-safe-restart.sh
# ───────────────────────────────────────────────────────────────

set -e

PORT=8001
DUCKDB_PATH="/home/sysop/brainswarm/data/cognitive.duckdb"
VENV="/home/sysop/brainswarm/venv/bin/activate"
API_CMD="/home/sysop/brainswarm/venv/bin/python -m uvicorn brainswarm.main:app --host 0.0.0.0 --port $PORT"

echo "───────────────────────────────────────────────────────────────"
echo "🧠  BrainSwarm Safe Restart Utility"
echo "───────────────────────────────────────────────────────────────"

# 1️⃣ Check and kill any processes using port 8001
echo "🔍 Checking for existing processes on port $PORT..."
if sudo lsof -i :$PORT >/dev/null 2>&1; then
  echo "⚠️  Port $PORT is in use. Terminating process..."
  sudo fuser -k ${PORT}/tcp || true
  sleep 1
  echo "✅  Port $PORT cleared."
else
  echo "✅  No port conflict detected."
fi

# 2️⃣ Kill any rogue uvicorn or Python BrainSwarm processes
echo "🔧 Cleaning up old BrainSwarm or uvicorn processes..."
pkill -f "uvicorn.*brainswarm.main" 2>/dev/null || true
pkill -f "brainswarm.main" 2>/dev/null || true
pkill -f "python.*brainswarm" 2>/dev/null || true
sleep 1

# 3️⃣ Check and fix DuckDB locks
if [ -f "${DUCKDB_PATH}.wal" ] || [ -f "${DUCKDB_PATH}.lock" ]; then
  echo "🧹 Cleaning DuckDB lock files..."
  mv "${DUCKDB_PATH}.wal" "${DUCKDB_PATH}.wal.backup.$(date +%s)" 2>/dev/null || true
  rm -f "${DUCKDB_PATH}.lock" 2>/dev/null || true
  echo "✅  DuckDB lock files cleared."
else
  echo "✅  No DuckDB lock files detected."
fi

# 4️⃣ Confirm virtual environment exists
if [ ! -f "$VENV" ]; then
  echo "❌ Virtual environment not found at $VENV"
  echo "   Please create it with: python3 -m venv /home/sysop/brainswarm/venv"
  exit 1
fi

# 5️⃣ Start BrainSwarm API
echo "🚀 Starting BrainSwarm API..."
source "$VENV"
nohup $API_CMD > /home/sysop/brainswarm/logs/restart.log 2>&1 &

sleep 2

if sudo lsof -i :$PORT >/dev/null 2>&1; then
  echo "✅  BrainSwarm API is now running on http://0.0.0.0:${PORT}"
  echo "📜  Logs: /home/sysop/brainswarm/logs/restart.log"
else
  echo "⚠️  Failed to detect BrainSwarm process on port ${PORT}. Check logs."
fi

echo "───────────────────────────────────────────────────────────────"
echo "🎯  Safe restart complete."
echo "───────────────────────────────────────────────────────────────"