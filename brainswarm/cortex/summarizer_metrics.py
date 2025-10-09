#!/usr/bin/env python3
# =====================================================================
# 🧠  BrainSwarm Cortex Summarizer — Prometheus Metrics Helper
# ---------------------------------------------------------------------
# Collects Prometheus counters and histograms for summarization runs.
# Metrics are served locally at http://localhost:9201/metrics
# =====================================================================

from prometheus_client import Counter, Histogram, start_http_server
import time

# --- Metrics definitions ---
SUMMARY_CYCLES_TOTAL = Counter(
    "brainswarm_summarizer_cycles_total",
    "Total number of summarization cycles completed"
)

SUMMARY_FAILURES_TOTAL = Counter(
    "brainswarm_summarizer_failures_total",
    "Number of summarization cycles that ended with an exception"
)

SUMMARY_DURATION_SECONDS = Histogram(
    "brainswarm_summarizer_cycle_duration_seconds",
    "Duration of each summarization cycle in seconds"
)

# --- Start exporter ---
def start_metrics_server(port: int = 9201):
    """Start background Prometheus metrics exporter."""
    start_http_server(port)
    print(f"🧩 Prometheus metrics exporter listening on :{port}")


# --- Decorator for summarization timing ---
def summarize_cycle(func):
    """Decorator to time and count summarization runs."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            SUMMARY_CYCLES_TOTAL.inc()
            return result
        except Exception:
            SUMMARY_FAILURES_TOTAL.inc()
            raise
        finally:
            SUMMARY_DURATION_SECONDS.observe(time.time() - start_time)
    return wrapper

# --- Main entry point ---
if __name__ == "__main__":
    start_metrics_server()
    import time
    while True:
        time.sleep(60)  # Keep running