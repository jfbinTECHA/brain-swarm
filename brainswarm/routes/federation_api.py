"""
Phase 8 – Federation API
HTTP endpoints for federation status and peer state exchange.
"""
from fastapi import APIRouter
import json
from ..federation import bridge

router = APIRouter()

@router.get("/federation/peers")
async def peers():
    """Return currently alive BrainSwarm peers on the LAN/Redis mesh."""
    return {"peers": bridge.get_peers()}

@router.get("/federation/state")
async def federation_state():
    """Return remote focus states collected from peers."""
    return {"states": bridge.collect_remote_focuses()}