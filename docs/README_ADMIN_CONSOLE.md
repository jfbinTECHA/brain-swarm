## 🧠 BrainSwarmOps Admin Console 1.0
**Unified System Health • Control • Telemetry**

---

### 📘 Overview
The **BrainSwarmOps Admin Console** provides a unified interface to **monitor**, **control**, and **audit** all system services in real time.
It integrates FastAPI, Next.js, Redis Streams, and Docker Compose into a live-operational control panel.

This dashboard is built for **DevOps engineers**, **AI swarm operators**, and **MLOps supervisors** managing distributed BrainSwarm nodes or deployments.

---

### 🧩 Core Features

| Feature | Description |
|----------|-------------|
| 🩺 **System Health Monitor** | Live status of API, DB, Redis, and Frontend (updates every 10 s) |
| 🧭 **System Control Panel** | One-click *Restart* and *Shutdown* for all containers |
| 🪵 **Recent Admin Actions** | Real-time Redis event feed of all admin and watchdog actions |
| 💬 **Toast Notifications** | Instant color-coded pop-ups for restart/shutdown results |
| 🔵 **Live Ops Indicator** | Pulsing teal light showing event stream activity |
| ⚙️ **Self-Healing Watchdog** | Auto-diagnostic Python agent restarting unhealthy containers |
| 🌌 **Theming** | Teal-on-graphite aesthetic for enterprise visual consistency |

---

### 🏗️ Architecture

```text
┌──────────────────────────────────────────┐
│          BrainSwarmOps Admin UI          │
│  Next.js + Tailwind + SSE + Toasts       │
│  ├── SystemHealth.tsx                    │
│  ├── AdminControls.tsx                   │
│  ├── AdminEvents.tsx                     │
│  ├── ToastManager.tsx                    │
│  └── LiveOpsIndicator.tsx                │
└──────────────────────────────────────────┘
             ▲             │
             │ SSE Stream  ▼
┌──────────────────────────────────────────┐
│          FastAPI Backend (API)           │
│  Routes: /healthz, /admin/shutdown,      │
│          /admin/restart, /admin/events   │
│  Logs admin actions → Redis stream       │
└──────────────────────────────────────────┘
             ▲
             │ Redis Stream (`admin_events`)
             ▼
┌──────────────────────────────────────────┐
│   Redis   │   Postgres   │   Watchdog    │
│  Cache +  │  Cortex DB   │  Self-healing │
│  Events   │              │  Diagnostics  │
└──────────────────────────────────────────┘
```

---

### ⚙️ Setup

```bash
git clone https://github.com/jfbinTECHA/brain-swarm.git
cd brain-swarm
docker compose up -d --build
```

Then open:

> 🔗 **http://localhost:3000/admin**

---

### 🧪 Testing the System

| Step | Command | Expected Output |
|------|----------|----------------|
| **1️⃣ Health Check** | `curl -s localhost:8001/healthz | jq` | `{ "status":"ok","db":"ok","redis":"ok" }` |
| **2️⃣ Restart Stack** | `curl -X POST localhost:8001/admin/restart` | Returns `{ "status":"ok" }` |
| **3️⃣ Inspect Logs** | `docker exec -it brainswarm-redis redis-cli XRANGE admin_events - +` | Shows recent restart/shutdown events |
| **4️⃣ Observe Dashboard** | [http://localhost:3000/admin](http://localhost:3000/admin) | Live update, toast notification, pulsing indicator |

---

### 🧭 Admin Console Layout

| Section | Function |
|----------|-----------|
| 🩺 **System Health Monitor** | Displays status of all key services |
| 🧭 **Control Panel** | Restart or shutdown the stack gracefully |
| 🪵 **Recent Actions Log** | Auto-updates from Redis via SSE |
| 💬 **Toast Alerts** | Teal (OK), Red (Error), Amber (Warn) pop-ups |
| 🔵 **Live Ops Indicator** | Pulses teal on every new event |
| ⚙️ **Self-Healing Watchdog** | Monitors `/healthz` and restarts services automatically |

---

### 🧠 Automation and Recovery

The `watchdog` container runs `/app/tools/health_watcher.py` and:

- Checks backend health every 60 s
- Logs any detected failure
- Restarts API/DB/Redis containers automatically
- Writes recovery events to the Redis `admin_events` stream

---

### 🧰 Maintenance Commands

| Purpose | Command |
|----------|----------|
| Stop all services | `docker compose down --remove-orphans` |
| Restart stack | `docker compose up -d --build` |
| View logs | `docker logs -f brainswarm-api` |
| Clear Redis stream | `docker exec -it brainswarm-redis redis-cli XTRIM admin_events MAXLEN 0` |
| Watchdog log file | `tail -f tools/logs/health_watcher.log` |

---

### 📊 Future Enhancements

| Planned Feature | Description |
|-----------------|--------------|
| 📡 **WebSocket broadcast** | Replace SSE with persistent socket channel for multi-admin sync |
| 🔒 **JWT authentication** | Secure `/admin/*` endpoints |
| 📈 **Grafana panel integration** | Embed Prometheus metrics directly into the console |
| 🧩 **Multi-node orchestration** | Expand control panel to manage remote BrainSwarm clusters |

---

### 🖼️ Screenshot Placeholders

> _Add these once your dashboard is live in production:_
- `docs/screenshots/admin-dashboard.png`
- `docs/screenshots/restart-toast.png`
- `docs/screenshots/live-ops-indicator.png`

---

### 🧠 Versioning
| Component | Version |
|------------|----------|
| **Admin Console** | `1.0` |
| **FastAPI** | `0.118.0` |
| **Next.js** | `14.x` |
| **Redis** | `7.x` |
| **Docker Compose** | `v2.25+` |

---

### 👤 Author & Maintainer
**Project Lead:** Joseph Buzzell ([@jfbinTECHA](https://github.com/jfbinTECHA))
**Stack:** Python 3.12 · FastAPI · Next.js · Redis · Docker · Tailwind · Framer Motion
**License:** MIT