from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui", response_class=HTMLResponse)
async def ui_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>🧠 BrainSwarm Neon Dashboard</title>
  <style>
    html,body{margin:0;padding:0;height:100%;font-family:'Segoe UI',sans-serif;background:radial-gradient(circle at center,#000010,#000);color:#fff;overflow:hidden;}
    header{background:#0a0a22;padding:0.8rem;text-align:center;font-size:1.5rem;color:#61a8ff;text-shadow:0 0 6px #61a8ff;}
    #info{padding:0.5rem;text-align:center;color:#7ec8ff;}
    canvas{position:absolute;top:4rem;left:0;right:0;bottom:0;margin:auto;display:block;width:100%;height:calc(100% - 4rem);}
    .hud{position:absolute;top:4.5rem;left:1rem;z-index:10;font-size:0.9rem;line-height:1.5;color:#9cf;}
    .hud div{margin-bottom:0.3rem;}
    table{position:absolute;bottom:0;left:0;width:100%;border-collapse:collapse;background:rgba(10,10,25,0.8);}
    .panel{position:absolute;top:4.5rem;right:1rem;background:rgba(10,10,25,0.8);padding:0.6rem;border:1px solid #223;border-radius:10px;color:#9cf;font-size:0.85rem;max-width:30%;}
    th,td{border:1px solid #223;padding:0.4rem 0.6rem;font-size:0.8rem;}
    th{color:#7ec8ff;background:#0a0a22;}
  </style>
</head>
<body>
  <header>🧠 BrainSwarm Neon Dashboard</header>
  <div id="info">Connecting...</div>
  <canvas id="viz"></canvas>
  <div class="hud" id="hud"></div>
  <div class="panel" id="concepts"><b>Concepts</b><div id="topc">—</div><hr style="border-color:#223"><b>Inferences</b><div id="infer">—</div></div>
  <table id="agents">
    <thead><tr><th>ID</th><th>Kind</th><th>CPU%</th><th>Mem MB</th><th>Tasks</th></tr></thead>
    <tbody></tbody>
  </table>

<script>
const ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/dashboard/ws');
const hud=document.getElementById('hud');
const info=document.getElementById('info');
const ctx=document.getElementById('viz').getContext('2d');
const tableBody=document.querySelector('#agents tbody');
let agents=[],edges=[],uptime=0,points=[];

function renderHUD(){
  hud.innerHTML='<div>Agents: '+agents.length+'</div>'+
                '<div>Edges: '+edges.length+'</div>'+
                '<div>Uptime: '+uptime+' s</div>';
}
function renderTable(){
  tableBody.innerHTML='';
  agents.forEach(a=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+a.id+'</td><td>'+a.kind+'</td><td>'+a.cpu.toFixed(1)+'</td><td>'+a.mem.toFixed(0)+'</td><td>'+a.tasks_inflight+'</td>';
    tableBody.appendChild(tr);
  });
}
function drawNetwork(){
  const w=ctx.canvas.width,h=ctx.canvas.height;
  ctx.clearRect(0,0,w,h);
  const n=agents.length;
  const radius=Math.min(w,h)/3;
  const cx=w/2,cy=h/2;
  const pos={};
  agents.forEach((a,i)=>{
    const ang=2*Math.PI*i/n;
    pos[a.id]={x:cx+radius*Math.cos(ang),y:cy+radius*Math.sin(ang)};
  });
  ctx.beginPath();ctx.strokeStyle='#0af3';
  edges.forEach(e=>{
    const s=pos[e.source],t=pos[e.target];
    if(s&&t){ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);}
  });
  ctx.stroke();
  agents.forEach(a=>{
    const p=pos[a.id];if(!p)return;
    ctx.beginPath();ctx.arc(p.x,p.y,8,0,Math.PI*2);
    ctx.fillStyle=a.online?'#0ff':'#555';ctx.fill();ctx.strokeStyle='#0ff8';ctx.stroke();
    ctx.font='10px monospace';ctx.fillStyle='#9cf';ctx.fillText(a.id,p.x+10,p.y+4);
  });
  points.push(agents.length);if(points.length>200)points.shift();
  ctx.beginPath();ctx.strokeStyle='#f0f';
  for(let i=0;i<points.length;i++){
    const x=i*(w/200),y=h-((points[i]||0)*3);
    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  }
  ctx.stroke();
}
function animate(){requestAnimationFrame(animate);drawNetwork();}
animate();
ws.onmessage=e=>{
  const d=JSON.parse(e.data);
  agents=d.agents||[];edges=d.edges||[];uptime=d.uptime_s||0;
  renderHUD();renderTable();
  info.textContent='Live ✓ '+new Date().toLocaleTimeString();
};
ws.onerror=()=>info.textContent='❌ WebSocket failed';
window.addEventListener('resize',()=>{ctx.canvas.width=innerWidth;ctx.canvas.height=innerHeight-80;});
window.dispatchEvent(new Event('resize'));

// === Live system stats HUD ===
const statsDiv=document.createElement('div');
statsDiv.id='sys-stats';
statsDiv.style.position='absolute';
statsDiv.style.top='0.5rem';
statsDiv.style.right='1rem';
statsDiv.style.color='#9cf';
statsDiv.style.fontSize='0.9rem';
document.body.appendChild(statsDiv);

async function updateSysStats(){
  try{
    const res=await fetch('/dashboard/sensors');
    const d=await res.json();
    statsDiv.innerHTML=`CPU ${d.cpu?.toFixed(1)||0}% | MEM ${d.memory?.toFixed(1)||0}% | DISK ${d.disk?.toFixed(1)||0}%`;
  }catch(e){statsDiv.innerHTML='(no sensors)';}
}
setInterval(updateSysStats,3000);
updateSysStats();

// === Focus HUD ===
const focusDiv=document.createElement('div');
focusDiv.id='focus';
focusDiv.style.position='absolute';
focusDiv.style.top='2.5rem';
focusDiv.style.left='1rem';
focusDiv.style.color='#0ff';
focusDiv.style.fontSize='1rem';
focusDiv.style.textShadow='0 0 6px #0ff';
document.body.appendChild(focusDiv);

async function updateFocus(){
  try{
    const res=await fetch('/dashboard/focus');
    const d=await res.json();
    focusDiv.innerHTML='Focus: '+(d.focus||'—');
  }catch(e){focusDiv.innerHTML='Focus: —'}
}
setInterval(updateFocus,4000);
updateFocus();

// === Concepts & Inferences panel ===
async function refreshConcepts(){
  try{
    const t = await fetch('/reason/top'); const tj = await t.json();
    const list = (tj.top||[]).map(([c,a])=>`${c} <span style="color:#7ec8ff">${a.toFixed(2)}</span>`).join('<br>');
    document.getElementById('topc').innerHTML = list || '—';

    // try inference from the top seed
    if((tj.top||[]).length){
      const seed = tj.top[0][0];
      const r = await fetch('/reason/infer?seed='+encodeURIComponent(seed));
      const rj = await r.json();
      const rel = (rj.related||[]).map(([c,w])=>`${seed} → ${c} <span style="color:#7ec8ff">${w.toFixed(2)}</span>`).join('<br>');
      document.getElementById('infer').innerHTML = rel || '—';
    }else{
      document.getElementById('infer').innerHTML = '—';
    }
  }catch(e){
    document.getElementById('topc').innerHTML = '(no data)';
    document.getElementById('infer').innerHTML = '—';
  }
}
setInterval(refreshConcepts, 5000);
refreshConcepts();
</script>
</body>
</html>
""")

