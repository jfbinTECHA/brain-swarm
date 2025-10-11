from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])

@router.get("/")
async def get_memory_status():
    """Simple health endpoint for the memory subsystem."""
    return {"status": "ok", "component": "memory", "message": "Memory system online (stub)"}