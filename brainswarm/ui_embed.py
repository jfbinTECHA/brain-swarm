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
    th,td{border:1px solid #223;padding:0.4rem 0.6rem;font-size:0.8rem;}
    th{color:#7ec8ff;background:#0a0a22;}
  </style>
</head>
<body>
  <header>🧠 BrainSwarm Neon Dashboard</header>
  <div id="info">Connecting to swarm...</div>
  <canvas id="viz"></canvas>
  <div class="hud" id="hud"></div>
  <table id="agents">
    <thead><tr><th>ID</th><th>Kind</th><th>Online</th><th>CPU</th><th>Mem</th><th>Tasks</th></tr></thead>
    <tbody></tbody>
  </table>

<script>
const ws = new WebSocket((location.protocol === 'https:'?'wss://':'ws://') + location.host + '/dashboard/ws');
const canvas = document.getElementById('viz');
const ctx = canvas.getContext('2d');
let agents = [], edges = [], uptime = 0;
let particles = [];

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight - 64;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  // Draw particles
  particles.forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
    ctx.fillStyle = p.color;
    ctx.fill();
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
    if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
  });
  // Draw edges
  ctx.strokeStyle = '#61a8ff';
  ctx.lineWidth = 1;
  edges.forEach(e => {
    const a1 = agents.find(a => a.id === e.source);
    const a2 = agents.find(a => a.id === e.target);
    if (a1 && a2) {
      ctx.beginPath();
      ctx.moveTo(a1.x, a1.y);
      ctx.lineTo(a2.x, a2.y);
      ctx.stroke();
    }
  });
  // Draw agents
  agents.forEach(a => {
    ctx.beginPath();
    ctx.arc(a.x, a.y, 12, 0, Math.PI*2);
    ctx.fillStyle = a.online ? '#00ff88' : '#ff4444';
    ctx.fill();
    ctx.strokeStyle = '#61a8ff';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#fff';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(a.id, a.x, a.y + 4);
  });
  requestAnimationFrame(draw);
}
draw();

ws.onmessage = ev => {
  const d = JSON.parse(ev.data);
  agents = d.agents.map((a, i) => ({
    ...a,
    x: 100 + (i % 10) * 80,
    y: 100 + Math.floor(i / 10) * 80
  }));
  edges = d.edges;
  uptime = d.uptime_s;
  document.getElementById('info').textContent = `Agents: ${d.agents.length} | Edges: ${d.edges.length} | Uptime: ${uptime}s`;
  const hud = document.getElementById('hud');
  hud.innerHTML = `
    <div>Cortex Mode: ${d.cortex?.mode || 'N/A'}</div>
    <div>Embeddings QPS: ${d.cortex?.embeddings_qps?.toFixed(3) || 0}</div>
    <div>Stream Lag: ${d.stream?.lag_ms || 0}ms</div>
    <div>Redis: ${d.redis_connected ? 'connected' : 'disconnected'}</div>
  `;
  const tbody = document.querySelector('#agents tbody');
  tbody.innerHTML = '';
  d.agents.forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${a.id}</td><td>${a.kind}</td><td>${a.online ? '✓' : '✗'}</td><td>${a.cpu.toFixed(1)}%</td><td>${a.mem.toFixed(0)} MB</td><td>${a.tasks_inflight}</td>`;
    tbody.appendChild(tr);
  });
  // Add particles
  if (particles.length < 50) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 3 + 1,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      color: `hsl(${Math.random() * 60 + 180}, 70%, 60%)`
    });
  }
};
ws.onerror = () => document.getElementById('info').textContent = '❌ Connection failed';
</script>
</body>
</html>
""")