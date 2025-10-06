#!/usr/bin/env python3
"""
Local Admin Console - Simple FastAPI app for system monitoring
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import psutil
import os

app = FastAPI(title="Local Admin Console", version="1.0.0")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/sysstats")
async def sysstats():
    """Get system statistics"""
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "mem": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent
    }

@app.get("/console", response_class=HTMLResponse)
async def console(request: Request):
    """Serve the unified console dashboard"""
    dashboards = [
        {"name": "Mission Control", "url": "/mission-control", "status": "UP"},
        {"name": "Grafana", "url": "http://localhost:3000", "status": "UP"},
        {"name": "Prometheus", "url": "http://localhost:9090", "status": "UP"},
    ]
    return templates.TemplateResponse("console.html", {"request": request, "dashboards": dashboards})

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Local Admin Console", "console": "/console", "sysstats": "/sysstats"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)