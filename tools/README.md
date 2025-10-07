## 🧠 BrainSwarmOps Self-Healing Watchdog

This tool runs inside a lightweight Python container (`brainswarm-watchdog`) and continuously monitors your stack health.

### 🩺 Function
- Checks the FastAPI `/healthz` endpoint every 60 seconds.
- Logs events to `tools/logs/health_watcher.log`.
- Restarts any unhealthy containers automatically (API, DB, Redis).
- Prevents infinite restart loops with safety delays.

### 📦 Included in docker-compose.yml
The service mounts the Docker socket for restart control:
```yaml
  watchdog:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./tools:/app
      - /var/run/docker.sock:/var/run/docker.sock
    command: ["python", "/app/health_watcher.py"]
```

### 🧾 Log Output Example
```json
{"status": "ok", "component": "redis", "timestamp": "2025-10-07T02:00:00Z"}
{"status": "error", "component": "db", "message": "db unhealthy → restarting...", "timestamp": "2025-10-07T02:05:00Z"}
```

### 🔧 Manual Run (outside Docker)
```bash
cd tools
python3 health_watcher.py
```

### ⚙️ Future Enhancements
- Redis Stream or API reporting of all self-heal events
- Slack or webhook alerts
- Dashboard integration of recent auto-fix logs