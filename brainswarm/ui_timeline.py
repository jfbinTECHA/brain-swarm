"""
Timeline UI page — Phase 6 Cognitive Analytics
Displays historical focus, confidence, and actions from DuckDB.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui/timeline", response_class=HTMLResponse)
async def timeline_page():
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'/>
<title>BrainSwarm Cognitive Timeline</title>
<style>
body{background:#0a0a22;color:#9cf;font-family:Segoe UI,Arial,sans-serif;margin:2rem;}
h1{color:#7ec8ff;text-shadow:0 0 8px #0ff;}
table{border-collapse:collapse;width:100%;margin-top:1rem;}
th,td{border:1px solid #223;padding:0.5rem;text-align:left;font-size:0.85rem;}
th{background:#0e0e33;color:#7ec8ff;}
#chart{height:120px;width:100%;margin-top:1rem;}
</style>
</head>
<body>
<h1>🧭 Cognitive Timeline</h1>
<canvas id="chart"></canvas>
<table id="timeline">
  <thead><tr><th>Time</th><th>Focus</th><th>Confidence</th><th>Actions</th></tr></thead>
  <tbody></tbody>
</table>
<script>
async function loadTimeline(){
  const res=await fetch('/dashboard/timeline?limit=50');
  const data=await res.json();
  const cycles=(data.cycles||[]).reverse();
  const tbody=document.querySelector('#timeline tbody');
  tbody.innerHTML='';
  const points=[];
  for(const c of cycles){
    const t=new Date(c.ts*1000).toLocaleTimeString();
    const acts=(c.actions||[]).join(', ');
    tbody.innerHTML+=`<tr><td>${t}</td><td>${c.focus}</td><td>${c.confidence.toFixed(2)}</td><td>${acts}</td></tr>`;
    points.push(c.confidence);
  }
  drawSparkline(points);
}

function drawSparkline(points){
  const c=document.getElementById('chart');
  const ctx=c.getContext('2d');
  const w=c.width=window.innerWidth-100;
  const h=c.height=120;
  ctx.clearRect(0,0,w,h);
  if(points.length<2) return;
  const max=Math.max(...points),min=Math.min(...points);
  const scaleY=(v)=>(h-20)-(v-min)/(max-min+0.0001)*(h-40);
  ctx.beginPath();
  ctx.moveTo(0,scaleY(points[0]));
  for(let i=1;i<points.length;i++){
    ctx.lineTo(i*(w/(points.length-1)),scaleY(points[i]));
  }
  ctx.strokeStyle='#0ff';
  ctx.lineWidth=2;
  ctx.shadowBlur=8;
  ctx.shadowColor='#0ff';
  ctx.stroke();
}

loadTimeline();
setInterval(loadTimeline,10000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)