#!/usr/bin/env python3
"""
BrainSwarmOps Self-Healing Watchdog

This service periodically checks the FastAPI /healthz endpoint,
logs system status, and automatically restarts any unhealthy containers.
"""
import os, time, requests, subprocess, datetime, json

API = os.getenv("HEALTH_API_URL", "http://api:8001/healthz")
LOG_PATH = "/app/logs/health_watcher.log"
CHECK_INTERVAL = int(os.getenv("HEALTH_INTERVAL", "60"))

def log_event(event: dict):
    """Append timestamped event to log file"""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    event["timestamp"] = datetime.datetime.utcnow().isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")


def restart_service(name: str):
    """Restart a service using docker compose"""
    print(f"🔧 Restarting {name}...")
    log_event({"action": "restart", "service": name})
    subprocess.run(["docker", "compose", "restart", name], check=False)


def check_and_fix():
    """Perform one full health check cycle"""
    try:
        res = requests.get(API, timeout=5)
        data = res.json()
    except Exception as e:
        msg = f"API unreachable: {e}"
        print("❌", msg)
        log_event({"status": "error", "component": "api", "message": msg})
        restart_service("api")
        return

    for svc in ["db", "redis"]:
        status = data.get(svc, "unknown")
        if status != "ok":
            msg = f"{svc} unhealthy → restarting..."
            print("⚠️ ", msg)
            log_event({"status": "error", "component": svc, "message": msg})
            restart_service(svc)
        else:
            print(f"✅ {svc} healthy")
            log_event({"status": "ok", "component": svc})


if __name__ == "__main__":
    print("🐕 BrainSwarmOps Health Watchdog started")
    while True:
        check_and_fix()
        time.sleep(CHECK_INTERVAL)