# BrainSwarm

## Quickstart

Run the following command to start BrainSwarm:

```bash
make quickstart
```

The system will automatically start all core services (API, Dashboard, Watchdog, Cortex, and Metrics).

---

### 🧠 Safe Restart (Recover from Port or DB Locks)

If BrainSwarm fails to start due to a port conflict or `DuckDB` lock, run:

```bash
./ops/brainswarm-safe-restart.sh
```

This script will safely clear locks, free port 8001, and relaunch the API.