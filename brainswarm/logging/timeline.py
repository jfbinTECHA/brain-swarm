"""
Phase 5 — Cognitive Timeline Logger (DuckDB)
Persists each cognitive cycle (focus, confidence, related, actions) for replay & introspection.
DB path: ./data/cognitive.duckdb
"""
from __future__ import annotations
import os, json, time, duckdb
from typing import Dict, List, Tuple

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "cognitive.duckdb"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_CONN = duckdb.connect(DB_PATH)
_CONN.execute("""
CREATE TABLE IF NOT EXISTS cognitive_timeline (
  ts DOUBLE,
  focus TEXT,
  confidence DOUBLE,
  related_json TEXT,
  actions_json TEXT
);
""")

def log_cycle(result: Dict, actions: List[str] | None = None) -> None:
    """
    Write one row per cycle to DuckDB.
    result is from cognitive.cognitive_step(); actions is planner output.
    """
    ts = float(result.get("timestamp", time.time()))
    focus = str(result.get("focus", "None"))
    confidence = float(result.get("confidence", 0.0))
    related = result.get("related", [])
    actions = actions or []
    _CONN.execute("""
    INSERT INTO cognitive_timeline (ts, focus, confidence, related_json, actions_json)
    VALUES (?, ?, ?, ?, ?)
    """, (ts, focus, confidence, json.dumps(related), json.dumps(actions)))