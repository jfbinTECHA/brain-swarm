# brainswarm.webhook_service.api
# Minimal stub for webhook handling in BrainSwarm

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/webhook/{source}")
async def receive_webhook(source: str, request: Request):
    """Stub endpoint for incoming webhooks."""
    data = await request.json()
    print(f"📨 Received webhook from {source}: {data}")
    return JSONResponse({"status": "received", "source": source, "data": data})
