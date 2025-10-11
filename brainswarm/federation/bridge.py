"""
Phase 8 – Federation Bridge
Enables multiple BrainSwarm instances to share their focus and actions over LAN or Redis Pub/Sub.
"""
from __future__ import annotations
import asyncio, json, time, socket, threading, redis, websockets

r = redis.from_url("redis://localhost:6379", decode_responses=True)
PEERS_KEY = "federation:peers"

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def broadcast_presence():
    node = local_ip()
    r.hset(PEERS_KEY, node, time.time())

def get_peers() -> list[str]:
    peers = r.hgetall(PEERS_KEY)
    now = time.time()
    alive = [ip for ip,ts in peers.items() if now-float(ts) < 60]
    return alive

async def serve_state(ws, path):
    while True:
        await asyncio.sleep(5)
        focus = r.get("current_focus")
        if focus:
            msg = json.dumps({"focus": json.loads(focus), "ts": time.time()})
            await ws.send(msg)

async def federation_server():
    async with websockets.serve(serve_state, "0.0.0.0", 8765):
        await asyncio.Future()

def federation_loop():
    """Background loop for presence broadcast."""
    while True:
        try:
            broadcast_presence()
        except Exception:
            pass
        time.sleep(15)

def start_background_bridge():
    """Launch server + presence threads."""
    threading.Thread(target=federation_loop, daemon=True).start()
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(federation_server(),), daemon=True).start()

def collect_remote_focuses() -> list[dict]:
    """Return focus states from other nodes recorded in Redis."""
    peers = get_peers()
    states=[]
    for ip in peers:
        try:
            key=f"federation:focus:{ip}"
            val=r.get(key)
            if val:
                states.append(json.loads(val))
        except Exception:
            pass
    return states