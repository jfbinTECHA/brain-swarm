"""
Phase 9 — Reflection Engine
Reads DuckDB cognitive timeline, derives trends and human-readable notes,
and stores them in Redis under 'reflective_notes'.
"""
from __future__ import annotations
import time, json, os
from typing import Dict, List, Tuple
import duckdb, redis

DB_PATH = "/home/sysop/brainswarm/data/cognitive.duckdb"
r = redis.from_url("redis://localhost:6379", decode_responses=True)

def _open_ro():
    return duckdb.connect(DB_PATH, read_only=True)

def _rows(limit:int=200) -> List[Tuple]:
    try:
        conn = _open_ro()
        rows = conn.execute(
            "SELECT ts, focus, confidence, related_json, actions_json "
            "FROM cognitive_timeline ORDER BY ts DESC LIMIT ?", [limit]
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []

def _freq(items: List[str]) -> Dict[str,int]:
    c: Dict[str,int] = {}
    for x in items:
        c[x] = c.get(x,0)+1
    return c

def _pct(n: int, d: int) -> float:
    return (100.0*n/d) if d else 0.0

def analyze(limit:int=200) -> Dict:
    rows = _rows(limit)
    if not rows:
        return {"summary":"No timeline data yet.","stats":{}, "ts": time.time()}

    focuses: List[str] = []
    confs: List[float] = []
    actions_all: List[str] = []

    for ts, focus, conf, relj, actj in rows:
        focuses.append(focus or "None")
        try:
            confs.append(float(conf or 0))
        except Exception:
            confs.append(0.0)
        # parse actions
        try:
            acts = json.loads(actj or "[]")
            if isinstance(acts, list):
                for a in acts:
                    actions_all.append(str(a))
        except Exception:
            pass

    # Top concepts / actions
    f_freq = _freq(focuses)
    a_freq = _freq(actions_all)
    total = len(focuses)
    top_focus = sorted(f_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    top_actions = sorted(a_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    avg_conf = sum(confs)/len(confs) if confs else 0.0

    # Simple trend: compare recent half vs. older half confidence
    mid = max(1, total//2)
    recent_avg = sum(confs[:mid])/max(1,len(confs[:mid]))
    older_avg  = sum(confs[mid:])/max(1,len(confs[mid:]))
    conf_trend = "rising" if recent_avg > older_avg+0.02 else ("falling" if recent_avg+0.02 < older_avg else "stable")

    # Stress vs comfort heuristics
    stress_hits  = sum(1 for f in focuses if "Stress" in f or "Pressure" in f or "HighCPU" in f)
    comfort_hits = sum(1 for f in focuses if "Comfort" in f or "Idle" in f)

    # Notes (compact, readable)
    notes = []
    if top_focus:
        tf = ", ".join([f"{k} ({_pct(v,total):.0f}%)" for k,v in top_focus])
        notes.append(f"Dominant focuses: {tf}.")
    notes.append(f"Average confidence: {avg_conf:.2f} ({conf_trend}).")
    if top_actions:
        ta = ", ".join([f"{k} ×{v}" for k,v in top_actions])
        notes.append(f"Most frequent actions: {ta}.")
    notes.append(f"Comfort vs Stress: {comfort_hits} comfort-like vs {stress_hits} stress-like cycles (last {total}).")

    out = {
        "summary": " ".join(notes),
        "stats": {
            "avg_confidence": round(avg_conf, 3),
            "confidence_trend": conf_trend,
            "top_focus": top_focus,
            "top_actions": top_actions,
            "comfort_hits": comfort_hits,
            "stress_hits": stress_hits,
            "total_cycles": total,
        },
        "ts": time.time(),
    }
    return out

def store_reflection(limit:int=200) -> Dict:
    data = analyze(limit=limit)
    r.set("reflective_notes", json.dumps(data))
    r.lpush("reflective_notes_history", json.dumps(data))
    r.ltrim("reflective_notes_history", 0, 99)  # keep latest 100
    return data