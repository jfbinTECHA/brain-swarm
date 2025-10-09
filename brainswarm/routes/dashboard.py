from __future__ import annotations
import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# ---- Optional Redis (graceful if missing) ----
try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None

router = APIRouter()

# ---------- Config (env / sensible defaults) ----------
REDIS_URL = (
    os.getenv("REDIS_URL")
    or os.getenv("redis_url")
    or "redis://localhost:6379"
)
# Streams (override via env if you already use other names)
STREAM_SUMMARY = os.getenv("CORTEX_SUMMARY_STREAM", "brainswarm:cortex:summary")
STREAM_EMBED = os.getenv("CORTEX_EMBED_STREAM", "brainswarm:cortex:embeddings")
STREAM_AGENT  = os.getenv("AGENT_EVENT_STREAM", "brainswarm:agents:events")

# ---------- Models ----------
class AgentStatus(BaseModel):
    id: str
    kind: str = "agent"
    online: bool = True
    cpu: float = 0.0
    mem: float = 0.0
    tasks_inflight: int = 0
    last_beat_ts: float = Field(default_factory=lambda: time.time())

class Edge(BaseModel):
    source: str
    target: str
    relation: str = "message"  # message|semantic|control

class CortexStatus(BaseModel):
    mode: str = "live"
    embeddings_qps: float = 0.0
    summarizer_interval_s: int = 300
    summarizer_last_ms: float = 0.0
    summarizer_last_status: str = "unknown"
    duckdb_path: Optional[str] = None

class StreamStats(BaseModel):
    summary_len: int = 0
    embed_len: int = 0
    agent_len: int = 0
    # simple lag approximation (last id timestamps)
    lag_ms: int = 0

class SwarmState(BaseModel):
    ts: float = Field(default_factory=lambda: time.time())
    uptime_s: int = 0
    agents: List[AgentStatus] = []
    edges: List[Edge] = []
    cortex: CortexStatus = CortexStatus()
    redis_connected: bool = False
    stream: StreamStats = StreamStats()
    notes: Optional[str] = None

# ---------- Hub ----------
class Hub:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._state: SwarmState = SwarmState()
        self._state_lock = asyncio.Lock()
        self._broadcast_q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._start_ts = time.time()
        self._redis = None
        self._last_embed_count = 0
        self._last_embed_ts = time.time()

    async def _redis_connect(self):
        if not aioredis:
            self._state.redis_connected = False
            return
        try:
            self._redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            await self._redis.ping()
            self._state.redis_connected = True
        except Exception:
            self._redis = None
            self._state.redis_connected = False

    async def init(self):
        await self._redis_connect()
        # seed demo nodes if empty
        if not self._state.agents:
            self._state.agents = [
                AgentStatus(id="cortex-summarizer", kind="service", cpu=1.1, mem=120.0),
                AgentStatus(id="bridge", kind="gateway", cpu=0.6, mem=88.0),
                AgentStatus(id="bytebot", kind="agent", cpu=2.0, mem=210.0),
            ]
            self._state.edges = [
                Edge(source="bridge", target="bytebot", relation="message"),
                Edge(source="bytebot", target="cortex-summarizer", relation="semantic"),
            ]

    # ---- Redis helpers ----
    async def _xlen(self, key: str) -> int:
        if not self._redis:
            return 0
        try:
            return int(await self._redis.xlen(key))
        except Exception:
            return 0

    async def _xrevrange_last(self, key: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Return (id, fields) of last entry, or None."""
        if not self._redis:
            return None
        try:
            entries = await self._redis.xrevrange(key, count=1)
            if entries:
                return entries[0]  # (id, dict)
        except Exception:
            return None
        return None

    @staticmethod
    def _ts_from_xid(xid: str) -> int:
        # XADD IDs are like "1717434890123-0" => ms since epoch
        try:
            return int(xid.split("-")[0])
        except Exception:
            return 0

    # ---- Telemetry collection ----
    async def _collect_stream_stats(self) -> None:
        summary_len = await self._xlen(STREAM_SUMMARY)
        embed_len   = await self._xlen(STREAM_EMBED)
        agent_len   = await self._xlen(STREAM_AGENT)

        # lag estimation from newest entry across streams
        latest_ms = 0
        for k in (STREAM_SUMMARY, STREAM_EMBED, STREAM_AGENT):
            item = await self._xrevrange_last(k)
            if item:
                ms = self._ts_from_xid(item[0])
                latest_ms = max(latest_ms, ms)
        now_ms = int(time.time() * 1000)
        lag_ms = max(0, now_ms - latest_ms) if latest_ms else 0

        self._state.stream = StreamStats(
            summary_len=summary_len,
            embed_len=embed_len,
            agent_len=agent_len,
            lag_ms=lag_ms,
        )

        # embeddings_qps (simple delta over time)
        now = time.time()
        delta_n = max(0, embed_len - self._last_embed_count)
        delta_t = max(0.001, now - self._last_embed_ts)
        self._state.cortex.embeddings_qps = round(delta_n / delta_t, 3)
        self._last_embed_count = embed_len
        self._last_embed_ts = now

    async def _collect_summary_signal(self) -> None:
        """Read last summarizer item to fill duration + status if provided by producer.
           Expected fields (if your summarizer writes them):
           - duration_ms
           - status ('ok'/'error')
           - interval_s (optional; also exposed as configured value)
        """
        item = await self._xrevrange_last(STREAM_SUMMARY)
        if not item:
            return
        _xid, fields = item
        dur = fields.get("duration_ms")
        status = fields.get("status")
        interval = fields.get("interval_s")
        try:
            if dur is not None:
                self._state.cortex.summarizer_last_ms = float(dur)
            if status:
                self._state.cortex.summarizer_last_status = str(status)
            if interval is not None:
                self._state.cortex.summarizer_interval_s = int(float(interval))
        except Exception:
            pass

    async def telemetry_loop(self):
        await self.init()
        while True:
            await asyncio.sleep(2.0)
            self._state.ts = time.time()
            self._state.uptime_s = int(self._state.ts - self._start_ts)

            # Try reconnect if Redis dropped
            if self._redis is None:
                await self._redis_connect()

            # Collect from Redis if available, else simulate gentle movement
            if self._redis:
                try:
                    await self._collect_stream_stats()
                    await self._collect_summary_signal()
                except Exception:
                    self._state.redis_connected = False
                    # fall through to simulation

            # light simulation decay for demo
            for a in self._state.agents:
                a.tasks_inflight = max(0, a.tasks_inflight - 1)

            await self._broadcast_q.put(self._state.model_dump())

    # ---- WS handling ----
    async def register(self, ws: WebSocket):
        await ws.accept()
        self._clients.add(ws)
        # instant snapshot
        await ws.send_text(json.dumps(self._state.model_dump()))

    def unregister(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def pump(self, ws: WebSocket):
        try:
            while True:
                msg = await self._broadcast_q.get()
                await ws.send_text(json.dumps(msg))
        except WebSocketDisconnect:
            self.unregister(ws)
        except Exception:
            self.unregister(ws)

hub = Hub()

# ---------- Routes ----------
@router.on_event("startup")
async def _start():
    asyncio.create_task(hub.telemetry_loop())

@router.get("/state", response_model=SwarmState)
async def get_state():
    return hub._state

@router.websocket("/ws")
async def ws_dashboard(socket: WebSocket):
    await hub.register(socket)
    await hub.pump(socket)