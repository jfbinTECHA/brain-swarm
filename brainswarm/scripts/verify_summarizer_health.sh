#!/usr/bin/env bash
# =====================================================================
# 🧠  BrainSwarm Cortex Summarizer Health Check
# ---------------------------------------------------------------------
# Checks:
#   • Systemd service state
#   • Recent log events for embedding/initialization success
# Returns:
#   • 0 = Healthy (service running + recent success event)
#   • 1 = Unhealthy (service stopped or recent errors)
#
# Can be run manually, via cron, or from Kilo Code automations.
# =====================================================================

SERVICE="brainswarm-summarizer.service"
LOGFILE="/home/sysop/brainswarm/logs/summarizer.log"
SUCCESS_PATTERN="Embedding adapter initialized successfully"
FAIL_PATTERN="Traceback"

# --- 1️⃣ Check if the service is active ---
if ! systemctl is-active --quiet "$SERVICE"; then
  echo "❌ Summarizer service not active"
  exit 1
fi

# --- 2️⃣ Verify recent log output (last 100 lines) ---
if [[ ! -f "$LOGFILE" ]]; then
  echo "⚠️  Log file not found: $LOGFILE"
  exit 1
fi

if tail -n 100 "$LOGFILE" | grep -q "$FAIL_PATTERN"; then
  echo "❌ Error detected in recent summarizer logs"
  exit 1
fi

if tail -n 100 "$LOGFILE" | grep -q "$SUCCESS_PATTERN"; then
  echo "✅ BrainSwarm Summarizer is healthy"
  exit 0
else
  echo "⚠️  No recent success event found — may be initializing"
  exit 1
fi