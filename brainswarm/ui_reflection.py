"""
Phase 9 — Reflection UI
Shows aggregated insights and the latest reflective notes.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui/reflection", response_class=HTMLResponse)
async def reflection_page():
    html = """<!DOCTYPE html>
<html><head><meta charset='utf-8'/>
<title>BrainSwarm Reflection</title>
<style>
body{background:#0a0a22;color:#9cf;font-family:Segoe UI,Arial,sans-serif;padding:2rem;}
h1{color:#7ec8ff;text-shadow:0 0 8px #0ff;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin-top:1.5rem;}
.card{background:rgba(10,10,25,0.8);border:1px solid #223;border-radius:10px;padding:1rem;box-shadow:0 0 10px #001;}
.title{color:#7ec8ff;font-weight:bold;}
.value{font-size:1.2rem;margin-top:.4rem;}
.notes{white-space:pre-wrap;margin-top:1rem;line-height:1.5;}
.btn{margin:.6rem 0;padding:.5rem .8rem;background:#0a2540;color:#9cf;border:1px solid #224;border-radius:8px;cursor:pointer;}
.btn:hover{filter:brightness(1.2);}
</style></head><body>
<h1>🪞 BrainSwarm Reflection</h1>
<button class="btn" onclick="runNow()">Run Reflection Now</button>
<div class="grid">
  <div class="card"><div class="title">Avg Confidence</div><div id="avg" class="value">–</div></div>
  <div class="card"><div class="title">Confidence Trend</div><div id="trend" class="value">–</div></div>
  <div class="card"><div class="title">Top Focus</div><div id="topf" class="value">–</div></div>
  <div class="card"><div class="title">Top Actions</div><div id="topa" class="value">–</div></div>
</div>
<div class="card notes" id="notes" style="margin-top:1rem;">–</div>
<script>
async function loadNotes(){
  const r = await fetch('/reflection/notes'); const d = await r.json();
  document.getElementById('notes').innerText = d.summary||'—';
  const s = d.stats||{};
  document.getElementById('avg').innerText = (s.avg_confidence??0).toFixed(2);
  document.getElementById('trend').innerText = s.confidence_trend||'—';
  const tf = (s.top_focus||[]).map(([k,v])=>k+' ×'+v).join(', ');
  const ta = (s.top_actions||[]).map(([k,v])=>k+' ×'+v).join(', ');
  document.getElementById('topf').innerText = tf||'—';
  document.getElementById('topa').innerText = ta||'—';
}
async function runNow(){
  await fetch('/reflection/run',{method:'POST'});
  setTimeout(loadNotes,500);
}
loadNotes(); setInterval(loadNotes,15000);
</script>
</body></html>"""
    return HTMLResponse(content=html)