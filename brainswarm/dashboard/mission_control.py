# brainswarm.dashboard.mission_control
# Temporary stub for the BrainSwarm Mission Control Dashboard

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

def get_mission_control_dashboard():
    """Return simple dashboard placeholder."""
    return {"status": "active", "message": "Mission Control Dashboard (stubbed)"}

def create_mission_control_html() -> str:
    """Return a basic HTML dashboard for development mode."""
    return """
    <html>
        <head><title>BrainSwarm Mission Control</title></head>
        <body style='background-color:#111; color:#0f0; font-family:monospace;'>
            <h1>🧠 BrainSwarm Mission Control (Stub)</h1>
            <p>Backend is running and dashboard endpoint is online.</p>
        </body>
    </html>
    """

# For FastAPI inclusion
@router.get("/dashboard", response_class=HTMLResponse)
async def mission_control():
    return HTMLResponse(create_mission_control_html())
