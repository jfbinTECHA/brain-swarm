"""
Concept Graph Reasoning (Phase 3 foundation)
 - Maintains an in-memory weighted concept graph (NetworkX).
 - Maps sensor metrics -> concepts (e.g., HighCPU, MemoryPressure).
 - Supports Hebbian-like strengthening and time-based decay.
 - Exposes helpers for top concepts and related inferences.
"""
from __future__ import annotations
import time
from typing import Dict, List, Tuple, Iterable
import networkx as nx

# Singleton graph
_G = nx.DiGraph()
_activation: Dict[str, float] = {}  # simple attention/activation score per concept
_last_update = time.time()

def _bump_activation(concept: str, amount: float = 1.0) -> None:
    _activation[concept] = _activation.get(concept, 0.0) + amount

def _decay_activation(halflife_s: float = 300.0) -> None:
    """Exponential decay on activations."""
    now = time.time()
    dt = now - _last_update
    if dt <= 0:
        return
    factor = 0.5 ** (dt / halflife_s)
    for k in list(_activation.keys()):
        _activation[k] *= factor
        if _activation[k] < 0.01:
            del _activation[k]

def ensure_node(concept: str) -> None:
    if concept not in _G:
        _G.add_node(concept, created=time.time())

def strengthen(a: str, b: str, step: float = 0.1) -> None:
    """Hebbian-like strengthening: if a & b co-occur, increase weight(a->b) and (b->a)."""
    ensure_node(a); ensure_node(b)
    w = _G.get_edge_data(a, b, {}).get("weight", 0.0) + step
    _G.add_edge(a, b, weight=w, updated=time.time())
    w2 = _G.get_edge_data(b, a, {}).get("weight", 0.0) + step
    _G.add_edge(b, a, weight=w2, updated=time.time())

def decay_edges(halflife_s: float = 3600.0) -> None:
    """Exponential decay on edges."""
    now = time.time()
    to_prune: List[Tuple[str, str]] = []
    for u, v, data in _G.edges(data=True):
        w = data.get("weight", 0.0)
        last = data.get("updated", now)
        dt = max(0.0, now - last)
        factor = 0.5 ** (dt / halflife_s)
        new_w = w * factor
        if new_w < 0.01:
            to_prune.append((u, v))
        else:
            _G[u][v]["weight"] = new_w
    for u, v in to_prune:
        _G.remove_edge(u, v)

def upsert_concepts(concepts: Iterable[str]) -> None:
    for c in concepts:
        ensure_node(c)
        _bump_activation(c, 0.2)

def cooccur(concepts: List[str], step: float = 0.1) -> None:
    n = len(concepts)
    for i in range(n):
        for j in range(i+1, n):
            strengthen(concepts[i], concepts[j], step=step)

def top_concepts(k: int = 10) -> List[Tuple[str, float]]:
    _decay_activation()
    return sorted(_activation.items(), key=lambda x: x[1], reverse=True)[:k]

def related(seed: str, k: int = 10) -> List[Tuple[str, float]]:
    """Return k neighbors of seed by outgoing weight."""
    if seed not in _G:
        return []
    nbrs = []
    for _, v, data in _G.out_edges(seed, data=True):
        nbrs.append((v, float(data.get("weight", 0.0))))
    nbrs.sort(key=lambda x: x[1], reverse=True)
    return nbrs[:k]

# --- Mapping from sensor metrics to concepts ---
def concepts_from_metrics(readings: Dict[str, float]) -> List[str]:
    c: List[str] = []
    cpu = readings.get("cpu", 0.0)
    mem = readings.get("memory", 0.0)
    disk = readings.get("disk", 0.0)

    # CPU
    if cpu >= 85: c.append("HighCPU")
    elif cpu >= 50: c.append("ModerateCPU")
    else: c.append("IdleCPU")

    # Memory
    if mem >= 85: c.append("MemoryPressure")
    elif mem >= 60: c.append("MemoryElevated")
    else: c.append("MemoryComfort")

    # Disk
    if disk >= 90: c.append("DiskPressure")
    elif disk >= 70: c.append("DiskElevated")
    else: c.append("DiskComfort")

    # Derived hints
    if "HighCPU" in c and "MemoryPressure" in c:
        c.append("SystemStress")
    if "IdleCPU" in c and "MemoryComfort" in c:
        c.append("SystemIdle")

    return c

def ingest_concepts_from_readings(readings: Dict[str, float]) -> Dict[str, List[str]]:
    """Map readings -> concepts and update graph."""
    cs = concepts_from_metrics(readings)
    upsert_concepts(cs)
    cooccur(cs, step=0.15)
    return {"concepts": cs}