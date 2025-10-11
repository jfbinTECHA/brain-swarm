"""
Edge tracker for BrainSwarm adaptive memory.
Implements Hebbian strengthening and time-based decay of connections.
"""

import time
import redis

# Default Redis connection (adjust URL if needed)
r = redis.from_url("redis://localhost:6379", decode_responses=True)

def record_edge(source: str, target: str, step: float = 0.1) -> None:
    """
    Strengthen the edge between source and target when used.
    """
    key = f"edge:{source}:{target}"
    now = time.time()
    pipe = r.pipeline()
    pipe.hset(key, mapping={"last_active": now})
    pipe.hincrbyfloat(key, "weight", step)
    pipe.execute()


def decay_edges(half_life: float = 3600.0) -> None:
    """
    Gradually weaken inactive edges over time (exponential decay).
    """
    now = time.time()
    for key in r.scan_iter("edge:*"):
        data = r.hgetall(key)
        if not data:
            continue
        last_active = float(data.get("last_active", 0))
        weight = float(data.get("weight", 0.1))
        dt = now - last_active
        decay = 0.5 ** (dt / half_life)
        new_weight = max(weight * decay, 0.01)
        r.hset(key, "weight", new_weight)


def get_edges():
    """
    Retrieve all edges and weights for visualization.
    """
    edges = []
    for key in r.scan_iter("edge:*"):
        try:
            _, s, t = key.split(":", 2)
            w = float(r.hget(key, "weight") or 0)
            edges.append({"source": s, "target": t, "weight": w})
        except Exception:
            continue
    return edges