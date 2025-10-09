from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
import os
from .routers import health
from .routes import dashboard as dashboard_routes

app = FastAPI(title="BrainSwarm API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(dashboard_routes.router, prefix="/dashboard", tags=["dashboard"])

@app.get("/")
def root():
    return {"message": "BrainSwarm API online"}

@app.get("/metrics")
def metrics():
    # Basic single-process export. If you use Gunicorn workers,
    # switch to multiprocess mode per prometheus_client docs.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Embedded lightweight UI ---
@app.get("/ui", response_class=HTMLResponse)
async def ui_page(request: Request):
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8"/>
          <title>🧠 BrainSwarm Dashboard</title>
          <style>
            body { background:#000; color:#fff; font-family:sans-serif; margin:0; padding:0; }
            header { background:#111; padding:1rem; font-size:1.5rem; color:#79a6ff; text-align:center; }
            #main { padding:1rem; display:flex; flex-direction:column; align-items:center; }
            #summary { margin-bottom:1rem; }
            table { border-collapse:collapse; width:80%; }
            th, td { border:1px solid #333; padding:0.5rem; text-align:left; }
            th { color:#79a6ff; background:#111; }
            canvas { background:#111; border:1px solid #333; margin-top:1rem; }
          </style>
        </head>
        <body>
          <header>🧠 BrainSwarm Internal Dashboard</header>
          <div id="main">
            <div id="summary">Connecting to swarm...</div>
            <table id="agents"><thead><tr><th>ID</th><th>Kind</th><th>Online</th><th>CPU</th><th>Mem</th><th>Tasks</th></tr></thead><tbody></tbody></table>
            <canvas id="chart" width="600" height="200"></canvas>
          </div>
          <script>
            const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/dashboard/ws');
            const ctx = document.getElementById('chart').getContext('2d');
            let points = [];

            function drawChart() {
              ctx.clearRect(0,0,600,200);
              ctx.strokeStyle = '#79a6ff';
              ctx.beginPath();
              for(let i=0;i<points.length;i++){
                const x = i*6, y = 200 - points[i]*10;
                if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
              }
              ctx.stroke();
            }

            ws.onmessage = (e) => {
              const d = JSON.parse(e.data);
              const summary = document.getElementById('summary');
              summary.textContent = 'Agents: ' + d.agents.length + ' | Edges: ' + d.edges.length + ' | Uptime: ' + d.uptime_s + 's';

              const tbody = document.querySelector('#agents tbody');
              tbody.innerHTML = '';
              d.agents.forEach(a=>{
                const tr=document.createElement('tr');
                tr.innerHTML='<td>'+a.id+'</td><td>'+a.kind+'</td><td>'+a.online+'</td><td>'+a.cpu.toFixed(1)+'%</td><td>'+a.mem.toFixed(0)+' MB</td><td>'+a.tasks_inflight+'</td>';
                tbody.appendChild(tr);
              });

              points.push(d.agents.length);
              if(points.length>100) points.shift();
              drawChart();
            };

            ws.onerror = ()=>{ document.getElementById('summary').textContent='❌ Connection failed'; };
          </script>
        </body>
        </html>
        """
    )
