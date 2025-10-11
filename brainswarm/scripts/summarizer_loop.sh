#!/usr/bin/env bash
# =====================================================================
# 🧠  BrainSwarm Cortex Summarizer Loop
# ---------------------------------------------------------------------
# Runs one summarization cycle every 300 seconds (5 min)
# Keeps the process resident to avoid systemd restart storms.
# =====================================================================

cd /home/sysop/brainswarm
source venv/bin/activate

while true; do
  echo "$(date '+%Y-%m-%d %H:%M:%S') — 🧠 Starting summarization cycle" >> /home/sysop/brainswarm/logs/summarizer.log
  # --- Launch metrics exporter if not already running ---
  if ! pgrep -f "brainswarm_summarizer_metrics" >/dev/null; then
      PYTHONPATH=/home/sysop/brainswarm python -m brainswarm.cortex.summarizer_metrics >> /home/sysop/brainswarm/logs/summarizer.log 2>&1 &
      echo "$(date '+%Y-%m-%d %H:%M:%S') — 📊 Started Prometheus metrics exporter on port 9201" >> /home/sysop/brainswarm/logs/summarizer.log
  fi

  # --- Run one summarization cycle with metrics instrumentation ---
  PYTHONPATH=/home/sysop/brainswarm python - <<'PYCODE' >> /home/sysop/brainswarm/logs/summarizer.log 2>&1
import asyncio
from brainswarm.cortex.summarizer import main as summarizer_main
from brainswarm.cortex.summarizer_metrics import summarize_cycle

@summarize_cycle
async def run_cycle():
    await summarizer_main()

asyncio.run(run_cycle())
PYCODE
  echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Cycle complete, sleeping 300 s" >> /home/sysop/brainswarm/logs/summarizer.log
  sleep 300
done

exit 0