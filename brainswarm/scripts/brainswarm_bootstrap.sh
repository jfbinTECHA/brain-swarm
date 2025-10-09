#!/usr/bin/env bash
# =====================================================================
# 🧠  BrainSwarmOps Bootstrap Script
# ---------------------------------------------------------------------
# Configures local node for full Cortex Summarizer automation:
#   1️⃣ Grants sysop passwordless sudo for summarizer restarts
#   2️⃣ Creates a cron job for periodic health checks
#   3️⃣ Adds webhook alert endpoint for recovery reports
# =====================================================================

set -e

SERVICE_NAME="brainswarm-summarizer.service"
VENVDIR="/home/sysop/brainswarm/venv"
WORKFLOW="/home/sysop/brainswarm/workflows/summarizer_health_check.yml"
WEBHOOK_URL="${BRAINSWARM_WEBHOOK_URL:-}"

echo "🚀 Bootstrapping BrainSwarmOps environment..."

# --- 1️⃣  Add passwordless sudo rule ---
SUDO_RULE="/etc/sudoers.d/brainswarm"
if [[ ! -f "$SUDO_RULE" ]]; then
  echo "sysop ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE_NAME}, /bin/systemctl start ${SERVICE_NAME}" | sudo tee "$SUDO_RULE" > /dev/null
  sudo chmod 440 "$SUDO_RULE"
  echo "✅ Added passwordless sudo rule for ${SERVICE_NAME}"
else
  echo "ℹ️  Sudo rule already exists: $SUDO_RULE"
fi

# --- 2️⃣  Schedule cron job for health checks every 15 minutes ---
CRON_JOB="*/15 * * * * source ${VENVDIR}/bin/activate && ${VENVDIR}/bin/kilo run ${WORKFLOW} >> /home/sysop/brainswarm/logs/health_auto.log 2>&1"
(sudo crontab -u sysop -l 2>/dev/null | grep -v kilo || true; echo "$CRON_JOB") | sudo crontab -u sysop -
echo "✅ Scheduled periodic health check workflow"

# --- 3️⃣  Optional webhook alert setup ---
if [[ -n "$WEBHOOK_URL" ]]; then
  ALERT_SCRIPT="/home/sysop/brainswarm/scripts/summarizer_recovery_alert.sh"
  cat <<EOF | sudo tee "$ALERT_SCRIPT" > /dev/null
#!/usr/bin/env bash
curl -X POST -H "Content-Type: application/json" -d '{
  "service": "BrainSwarm Cortex Summarizer",
  "event": "Auto-Recovery Triggered",
  "timestamp": "'\$(date +%Y-%m-%dT%H:%M:%S%z)'"
}' "$WEBHOOK_URL"
EOF
  sudo chmod +x "$ALERT_SCRIPT"
  echo "✅ Webhook alert script created at: $ALERT_SCRIPT"
else
  echo "ℹ️  No BRAINSWARM_WEBHOOK_URL defined — skipping alert integration."
fi

echo "🎯 Bootstrap complete. Node ready for full summarizer automation."

# =====================================================================
# 🧩  BRAINSWARM MONITORING REGISTRATION
# ---------------------------------------------------------------------
# Adds local Prometheus scrape target & Grafana dashboard
# =====================================================================

PROM_DIR="/etc/prometheus"
SCRAPE_FILE="${PROM_DIR}/brainswarm_scrape.yml"
GRAFANA_DIR="/var/lib/grafana/dashboards"
GRAFANA_DASH="/home/sysop/brainswarm/dashboards/cortex_summarizer_metrics.json"

# --- 4️⃣  Configure Prometheus scrape target ---
if [[ -d "$PROM_DIR" ]]; then
  echo "✅ Prometheus config directory detected: $PROM_DIR"

  if [[ ! -f "$SCRAPE_FILE" ]]; then
    sudo tee "$SCRAPE_FILE" > /dev/null <<EOF
scrape_configs:
  - job_name: 'brainswarm-summarizer'
    static_configs:
      - targets: ['localhost:9201']
EOF
    echo "✅ Created Prometheus scrape file: $SCRAPE_FILE"
  else
    echo "ℹ️  Scrape file already exists: $SCRAPE_FILE"
  fi

  if grep -q "brainswarm-summarizer" "$PROM_DIR/prometheus.yml" 2>/dev/null; then
    echo "ℹ️  Prometheus already includes brainswarm-summarizer job."
  else
    echo "✅ Appending scrape include to prometheus.yml..."
    sudo sed -i '/scrape_configs:/a\  - job_name: brainswarm-summarizer\n    file_sd_configs:\n      - files: ["'"$SCRAPE_FILE"'"]' "$PROM_DIR/prometheus.yml"
  fi

  sudo systemctl restart prometheus || echo "⚠️  Could not restart Prometheus (check permissions)"
else
  echo "⚠️  Prometheus directory not found. Skipping scrape registration."
fi

# --- 5️⃣  Install Grafana dashboard for summarizer metrics ---
if [[ -d "$GRAFANA_DIR" && -f "$GRAFANA_DASH" ]]; then
  sudo mkdir -p "$GRAFANA_DIR"
  sudo cp "$GRAFANA_DASH" "$GRAFANA_DIR/brainswarm_cortex_summarizer.json"
  echo "✅ Installed Grafana dashboard at $GRAFANA_DIR/brainswarm_cortex_summarizer.json"
  echo "ℹ️  Restart Grafana to load new dashboard: sudo systemctl restart grafana-server"
else
  echo "⚠️  Grafana directory or dashboard not found. Skipping dashboard import."
fi

echo "📊 Monitoring registration complete — Prometheus + Grafana linked."

# =====================================================================
# 🛰  WEBHOOK TELEMETRY INTEGRATION REMINDER
# ---------------------------------------------------------------------
# Prompts user to define BRAINSWARM_WEBHOOK_URL for recovery alerts
# =====================================================================

if ! grep -q "BRAINSWARM_WEBHOOK_URL" /home/sysop/brainswarm/.env 2>/dev/null; then
  echo "" | sudo tee -a /home/sysop/brainswarm/.env > /dev/null
  echo "# === Telemetry Configuration ===" | sudo tee -a /home/sysop/brainswarm/.env > /dev/null
  echo "BRAINSWARM_WEBHOOK_URL=" | sudo tee -a /home/sysop/brainswarm/.env > /dev/null
  echo "ℹ️  Added BRAINSWARM_WEBHOOK_URL placeholder to .env (please set your Ops webhook URL)."
else
  echo "✅ Webhook environment variable already present in .env"
fi

echo "🛰 Webhook telemetry system ready — set BRAINSWARM_WEBHOOK_URL to enable live Ops alerts."

# =====================================================================
# END OF BRAINSWARM OPS BOOTSTRAP
# =====================================================================