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
  <title>🧠 BrainSwarm UI</title>
  <style>
    body {background:#000;color:#fff;font-family:sans-serif;margin:0;padding:0;}
    header{background:#111;padding:1rem;text-align:center;font-size:1.5rem;color:#79a6ff;}
    table{border-collapse:collapse;margin:auto;width:80%;margin-top:1rem;}
    th,td{border:1px solid #333;padding:0.5rem;}
    th{background:#111;color:#79a6ff;}
    #summary{text-align:center;padding:1rem;}
  </style>
</head>
<body>
  <header>🧠 BrainSwarm Internal Dashboard</header>
  <div id="summary">Connecting...</div>
  <table id="agents">
    <thead><tr><th>ID</th><th>Kind</th><th>Online</th><th>CPU</th><th>Mem</th><th>Tasks</th></tr></thead>
    <tbody></tbody>
  </table>

<script>
const ws = new WebSocket((location.protocol === 'https:'?'wss://':'ws://') + location.host + '/dashboard/ws');
ws.onmessage = ev => {
  const d = JSON.parse(ev.data);
  document.getElementById('summary').textContent =
    'Agents: ' + d.agents.length + ' | Edges: ' + d.edges.length + ' | Uptime: ' + d.uptime_s + 's';
  const tbody=document.querySelector('#agents tbody');
  tbody.innerHTML='';
  d.agents.forEach(a=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+a.id+'</td><td>'+a.kind+'</td><td>'+a.online+'</td><td>'+a.cpu.toFixed(1)+'%</td><td>'+a.mem.toFixed(0)+' MB</td><td>'+a.tasks_inflight+'</td>';
    tbody.appendChild(tr);
  });
};
ws.onerror = ()=>document.getElementById('summary').textContent='❌ connection failed';
</script>
</body>
</html>
""")