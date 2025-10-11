"""
Phase 8 – Federation Dashboard UI
Visualizes active peers and their current focus concepts.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui/federation", response_class=HTMLResponse)
async def federation_ui():
    html = """<!DOCTYPE html><html><head>
<meta charset='utf-8'/>
<title>BrainSwarm Federation Bridge</title>
<style>
body{background:#0a0a22;color:#9cf;font-family:Segoe UI,Arial,sans-serif;padding:2rem;}
h1{color:#7ec8ff;text-shadow:0 0 8px #0ff;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin-top:1.5rem;}
.card{background:rgba(10,10,25,0.8);border:1px solid #223;border-radius:10px;padding:1rem;box-shadow:0 0 10px #001;}
.title{color:#7ec8ff;font-weight:bold;}
.value{font-size:1.1rem;margin-top:.4rem;}
</style></head><body>
<h1>🌐 BrainSwarm Federation Network</h1>
<div class="grid" id="peers"></div>
<script>
async function refresh(){
  const r = await fetch('/federation/peers'); const p = await r.json();
  const s = await fetch('/federation/state'); const d = await s.json();
  const peers = p.peers || []; const states = d.states || [];
  const div = document.getElementById('peers'); div.innerHTML = '';
  for (const ip of peers){
    const st = states.find(x=>x.node===ip);
    div.innerHTML += `<div class="card"><div class="title">${ip}</div><div class="value">${st?st.focus.focus:"—"}</div></div>`;
  }
}
refresh(); setInterval(refresh,10000);
</script></body></html>"""
    return HTMLResponse(content=html)