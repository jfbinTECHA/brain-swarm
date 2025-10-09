"""
Phase 9 — Reflection API
Endpoints to compute and fetch reflective notes.
"""
from fastapi import APIRouter
import json, redis
from brainswarm.reflection.engine import store_reflection

router = APIRouter()
_r = redis.from_url("redis://localhost:6379", decode_responses=True)

@router.post("/reflection/run")
async def reflection_run(limit:int=200):
    """Compute reflection now and store in Redis."""
    res = store_reflection(limit=limit)
    return res

@router.get("/reflection/notes")
async def reflection_notes():
    """Return latest reflective notes."""
    val = _r.get("reflective_notes")
    return json.loads(val) if val else {"summary":"No reflections yet."}