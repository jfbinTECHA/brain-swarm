#!/bin/bash

# 🧠 BrainSwarm API — Ngrok Reset & Reconnect Script
# This script ensures ngrok is fully cleaned, re-authenticated, and serving the BrainSwarm API on port 8001.

echo "──────────────────────────────"
echo "🌐 Resetting ngrok environment"
echo "──────────────────────────────"

# 1️⃣ Kill all existing ngrok processes
echo "🧹 Killing old ngrok processes..."
pkill ngrok || true
sleep 2

# 2️⃣ Verify that no ngrok process is still running
if pgrep ngrok > /dev/null; then
  echo "❌ ngrok process still running, forcing kill..."
  sudo kill -9 $(pgrep ngrok) || true
else
  echo "✅ No active ngrok processes."
fi

# 3️⃣ Clean up old configs and session data
echo "🗑️ Removing old config files..."
rm -rf ~/.config/ngrok/ngrok.yml
rm -rf ~/.ngrok2
echo "✅ Configs cleared."

# 4️⃣ (Optional) Verify local API health
echo "📡 Checking local BrainSwarm API status..."
curl -s http://localhost:8001/api || echo "⚠️ API not responding on localhost:8001 yet — check service."

# 5️⃣ Add your new ngrok authtoken
echo "🔑 Adding ngrok authtoken..."
ngrok config add-authtoken 33a7PkUiLIvXOsj9NHbN25GuwQr_212kDbKVMYukzgeFyUp4e

# 6️⃣ Launch the new tunnel
echo "🚀 Launching ngrok tunnel for BrainSwarm API..."
ngrok http http://localhost:8001