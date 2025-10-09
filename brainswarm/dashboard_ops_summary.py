#!/usr/bin/env python3
# =====================================================================
# 🧠  BrainSwarmOps Summary Dashboard
# ---------------------------------------------------------------------
# Displays system and service health in a simple web interface.
# =====================================================================

from flask import Flask, jsonify, render_template_string
import os, subprocess, time, psutil, requests

app = Flask(__name__)

LOG_VERIFY = "/home/sysop/brainswarm/logs/ops_autofix_cron.log"
LOG_SUMMARIZER = "/home/sysop/brainswarm/logs/summarizer.log"

def check_service(name):
    try:
        subprocess.run(["systemctl", "is-active", "--quiet", name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_url(url):
    try:
        r = requests.get(url, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def check_file(path):
    return os.path.exists(path)

def tail_log(path, n=3):
    if not os.path.exists(path): return []
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()[-n:]
    return [line.strip() for line in lines]

@app.route("/")
def index():
    data = {
        "summarizer_active": check_service("brainswarm-summarizer.service"),
        "redis_active": check_service("redis-server.service"),
        "chroma_up": check_url("http://localhost:8000/api/v1/heartbeat"),
        "metrics_up": check_url("http://localhost:9201/metrics"),
        "duckdb_exists": check_file("/home/sysop/brainswarm/data/cortex.duckdb"),
        "last_verify": time.ctime(os.path.getmtime(LOG_VERIFY)) if check_file(LOG_VERIFY) else "Never",
        "last_summarizer_update": time.ctime(os.path.getmtime(LOG_SUMMARIZER)) if check_file(LOG_SUMMARIZER) else "Never",
        "cpu": psutil.cpu_percent(interval=0.5),
        "mem": psutil.virtual_memory().percent,
        "verify_tail": tail_log(LOG_VERIFY),
        "sum_tail": tail_log(LOG_SUMMARIZER),
    }
    html = f"""
    <html><head><title>🧠 BrainSwarmOps Summary</title>
    <style>
      body {{ font-family: Arial; background-color:#0f172a; color:#e2e8f0; padding:20px; }}
      .card {{ background:#1e293b; padding:15px; border-radius:10px; margin-bottom:15px; }}
      h1 {{ color:#38bdf8; }}
      .ok {{ color:#22c55e; }}
      .fail {{ color:#ef4444; }}
      .warn {{ color:#facc15; }}
      pre {{ background:#0f172a; padding:10px; border-radius:8px; color:#94a3b8; }}
    </style></head>
    <body>
    <h1>🧠 BrainSwarmOps Summary Dashboard</h1>
    <div class='card'><b>System</b><br>
    CPU: {data['cpu']}% &nbsp; Memory: {data['mem']}%
    </div>

    <div class='card'><b>Services</b><br>
    Summarizer: <span class='{ 'ok' if data['summarizer_active'] else 'fail' }'>{ 'Active' if data['summarizer_active'] else 'Down' }</span><br>
    Redis: <span class='{ 'ok' if data['redis_active'] else 'fail' }'>{ 'Active' if data['redis_active'] else 'Down' }</span><br>
    Chroma: <span class='{ 'ok' if data['chroma_up'] else 'fail' }'>{ 'Online' if data['chroma_up'] else 'Offline' }</span><br>
    Metrics Exporter: <span class='{ 'ok' if data['metrics_up'] else 'fail' }'>{ 'Online' if data['metrics_up'] else 'Offline' }</span><br>
    DuckDB: <span class='{ 'ok' if data['duckdb_exists'] else 'fail' }'>{ 'Found' if data['duckdb_exists'] else 'Missing' }</span>
    </div>

    <div class='card'><b>Last Activity</b><br>
    Verification Run: {data['last_verify']}<br>
    Summarizer Log: {data['last_summarizer_update']}
    </div>

    <div class='card'><b>Recent Verification Log</b>
    <pre>{chr(10).join(data['verify_tail'])}</pre></div>

    <div class='card'><b>Recent Summarizer Log</b>
    <pre>{chr(10).join(data['sum_tail'])}</pre></div>

    <div class='card'><b>Status</b><br>
    <span class='{"ok" if all([data['summarizer_active'],data['redis_active'],data['chroma_up'],data['metrics_up']]) else "warn"}'>
      {'✅ All systems operational' if all([data['summarizer_active'],data['redis_active'],data['chroma_up'],data['metrics_up']]) else '⚠️ Some components need attention'}
    </span></div>
    </body></html>
    """
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9202)