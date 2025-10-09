"""
Phase 5 — Planner
Maps focus concepts -> symbolic actions and emits them to Redis action_stream.
This is intentionally simple: a rules table that you can expand later.
"""
from __future__ import annotations
import time, redis
from typing import Dict, List, Tuple

r = redis.from_url("redis://localhost:6379", decode_responses=True)

# Simple concept -> action rules (extend as needed)
RULES: List[Tuple[str, str]] = [
    ("SystemStress", "reduce_load"),
    ("HighCPU", "scale_workers"),
    ("MemoryPressure", "cleanup_cache"),
    ("DiskPressure", "compress_logs"),
    ("SystemIdle", "run_summarization"),
    ("MemoryComfort", "maintain_state"),
]

def _choose_actions(focus: str, related: List[Tuple[str, float]]) -> List[str]:
    """Return a (small) set of actions based on focus and nearest related concepts."""
    actions: List[str] = []
    def add_if_match(concept: str):
        for pattern, act in RULES:
            if pattern in concept and act not in actions:
                actions.append(act)
    add_if_match(focus or "")
    for c, _w in related[:4]:
        add_if_match(c)
    # fallback
    if not actions:
        actions = ["log_state"]
    return actions[:3]

def plan_and_emit(cycle_result: Dict) -> Dict:
    """
    Takes the result from cognitive.cognitive_step() and emits action messages.
    Returns a summary dict {"focus":..., "actions":[...]}.
    """
    focus = cycle_result.get("focus") or "None"
    related = cycle_result.get("related") or []
    actions = _choose_actions(focus, related)
    now = time.time()
    for act in actions:
        r.xadd("action_stream", {
            "ts": now,
            "focus": focus,
            "action": act,
        })
    return {"focus": focus, "actions": actions, "ts": now}