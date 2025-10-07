from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.post("/shutdown")
def shutdown_stack():
    """
    Gracefully shuts down all BrainSwarmOps containers via docker compose.
    """
    try:
        cmd = ["docker", "compose", "down", "--remove-orphans"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/restart")
def restart_stack():
    """
    Restarts all BrainSwarmOps containers gracefully.
    """
    try:
        stop = subprocess.run(["docker", "compose", "down"], capture_output=True, text=True)
        start = subprocess.run(["docker", "compose", "up", "-d", "--build"], capture_output=True, text=True)
        return {
            "status": "ok" if start.returncode == 0 else "error",
            "stdout": start.stdout.strip(),
            "stderr": start.stderr.strip(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Simple Redis audit logger
import redis, os, datetime, json

def log_admin_action(action: str, result: str):
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "result": result,
        }
        r.xadd("admin_events", {"event": json.dumps(event)})
    except Exception:
        pass  # silently ignore if redis not available


@router.get("/events")
def get_admin_events(limit: int = 10):
    """
    Retrieve the most recent admin events from Redis stream.
    """
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        entries = r.xrevrange("admin_events", count=limit)
        events = []
        for entry in entries:
            event_data = json.loads(entry[1].get(b"event", b"{}"))
            events.append(event_data)
        return {"events": events}
    except Exception as e:
        return {"error": str(e), "events": []}


# --- Real-time SSE stream for admin events ---
from fastapi.responses import StreamingResponse
import asyncio


@router.get("/events/stream")
async def stream_admin_events():
    """
    Server-Sent Events stream for live admin actions.
    """
    async def event_generator():
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        last_id = "$"  # start from newest
        while True:
            try:
                msgs = r.xread({"admin_events": last_id}, block=10000, count=1)
                if msgs:
                    stream, entries = msgs[0]
                    for entry_id, fields in entries:
                        event_data = fields.get(b"event", b"{}").decode()
                        yield f"data: {event_data}\n\n"
                        last_id = entry_id.decode()
            except Exception:
                await asyncio.sleep(2)
                continue

    return StreamingResponse(event_generator(), media_type="text/event-stream")