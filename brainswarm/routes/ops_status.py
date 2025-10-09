"""
Phase 7 – Maintenance & Health Status Endpoints
Provides /dashboard/ops/status and /dashboard/ops/metrics for operational monitoring.
"""
from fastapi import APIRouter, Response
import os, time, psutil, redis, duckdb, json

r = redis.from_url("redis://localhost:6379", decode_responses=True)
router = APIRouter()

def _duckdb_size() -> float:
    try:
        p = "/home/sysop/brainswarm/data/cognitive.duckdb"
        return os.path.getsize(p)/1e6
    except Exception:
        return 0.0

def _avg_cycle_time(limit:int=20)->float:
    try:
        conn = duckdb.connect("/home/sysop/brainswarm/data/cognitive.duckdb", read_only=True)
        res = conn.execute(
            "SELECT ts FROM cognitive_timeline ORDER BY ts DESC LIMIT ?",[limit]
        ).fetchall()
        conn.close()
        if len(res) > 1:
            diffs=[res[i][0]-res[i+1][0] for i in range(len(res)-1)]
            return sum(diffs)/len(diffs)
    except Exception:
        pass
    return 0.0

def _redis_info():
    try:
        i = r.info()
        return {"used_memory_mb": round(i.get("used_memory",0)/1e6,2),
                "connected_clients": i.get("connected_clients",0)}
    except Exception:
        return {"used_memory_mb":0,"connected_clients":0}

@router.get("/dashboard/ops/status")
async def ops_status():
    p = psutil.Process(os.getpid())
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory().percent
    uptime = time.time()-p.create_time()
    redis_i=_redis_info()
    duck_size=_duckdb_size()
    cyc=_avg_cycle_time()
    return {
        "cpu_percent": cpu,
        "memory_percent": mem,
        "uptime_s": int(uptime),
        "redis": redis_i,
        "duckdb_size_mb": duck_size,
        "avg_cycle_interval_s": round(cyc,1)
    }

@router.get("/dashboard/ops/metrics")
async def ops_metrics():
    d=await ops_status()
    out=[]
    def line(k,v): out.append(f"{k} {v}")
    line("brainswarm_cpu_percent",d["cpu_percent"])
    line("brainswarm_memory_percent",d["memory_percent"])
    line("brainswarm_uptime_seconds",d["uptime_s"])
    line("brainswarm_duckdb_size_mb",d["duckdb_size_mb"])
    line("brainswarm_cycle_interval_seconds",d["avg_cycle_interval_s"])
    line("brainswarm_redis_memory_mb",d["redis"]["used_memory_mb"])
    return Response("\n".join(out), media_type="text/plain")