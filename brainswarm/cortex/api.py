from fastapi import APIRouter

router = APIRouter(prefix="/cortex", tags=["cortex"])

@router.get("/")
async def get_cortex_status():
    """Simple health endpoint for the cortex subsystem."""
    return {"status": "ok", "component": "cortex", "message": "Cortex subsystem operational (stub)"}