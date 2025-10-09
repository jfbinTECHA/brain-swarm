"""
Phase 7 – Maintenance Dashboard UI
Displays uptime, CPU/mem, Redis stats, DuckDB size, and average cycle timing.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui/maintenance", response_class=HTMLResponse)
async def maintenance_page():
    html = """<!DOCTYPE html>
<html><head><meta charset='utf-8'/>
<title>BrainSwarm Maintenance Dashboard</title>
<style>
body{background:#0a0a22;color:#9cf;font-family:Segoe UI,Arial,sans-serif;padding:2rem;}
h1{color:#7ec8ff;text-shadow:0 0 8px #0ff;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin-top:1.5rem;}
.card{background:rgba(10,10,25,0.8);border:1px solid #223;border-radius:10px;padding:1rem;box-shadow:0 0 10px #001;}
.title{color:#7ec8ff;font-weight:bold;}
.value{font-size:1.3rem;margin-top:.4rem;}
</style></head><body>
<h1>🛠 BrainSwarmOps Health Dashboard</h1>
<div class="grid">
  <div class="card"><div class="title">CPU Load</div><div id="cpu" class="value">–</div></div>
  <div class="card"><div class="title">Memory Usage</div><div id="mem" class="value">–</div></div>
  <div class="card"><div class="title">Uptime (s)</div><div id="upt" class="value">–</div></div>
  <div class="card"><div class="title">Redis Memory (MB)</div><div id="rmem" class="value">–</div></div>
  <div class="card"><div class="title">DuckDB Size (MB)</div><div id="ddb" class="value">–</div></div>
  <div class="card"><div class="title">Cycle Interval (s)</div><div id="cyc" class="value">–</div></div>
</div>
<script>
async function updateStats(){
  try{
    const res=await fetch('/dashboard/ops/status');
    const d=await res.json();
    document.getElementById('cpu').textContent=d.cpu_percent.toFixed(1)+'%';
    document.getElementById('mem').textContent=d.memory_percent.toFixed(1)+'%';
    document.getElementById('upt').textContent=d.uptime_s;
    document.getElementById('rmem').textContent=d.redis.used_memory_mb.toFixed(1);
    document.getElementById('ddb').textContent=d.duckdb_size_mb.toFixed(1);
    document.getElementById('cyc').textContent=d.avg_cycle_interval_s.toFixed(1);
  }catch(e){
    console.error('Stats update failed:',e);
  }
}
updateStats();
setInterval(updateStats,5000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)