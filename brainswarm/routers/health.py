from fastapi import APIRouter
import socket
import datetime
import psutil

router = APIRouter()

@router.get("/")
async def health_check():
    """Lightweight system health probe."""
    return {
        "status": "ok",
        "service": "brainswarm-api",
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "details": {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "active_pids": len(psutil.pids()),
        },
    }