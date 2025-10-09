"use client";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

type AgentStatus = {
  id: string; kind: string; online: boolean; cpu: number; mem: number; tasks_inflight: number; last_beat_ts: number;
};
type Edge = { source: string; target: string; relation: string };
type CortexStatus = {
  mode: string; embeddings_qps: number; summarizer_interval_s: number; summarizer_last_ms: number; summarizer_last_status: string; duckdb_path?: string | null;
};
type StreamStats = { summary_len: number; embed_len: number; agent_len: number; lag_ms: number };
type SwarmState = {
  ts: number; uptime_s: number; agents: AgentStatus[]; edges: Edge[];
  cortex: CortexStatus; redis_connected: boolean; stream: StreamStats; notes?: string | null;
};

function wsUrlFromHttp(httpUrl: string) {
  const u = new URL(httpUrl);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.pathname = "/dashboard/ws";
  return u.toString();
}
function useSwarmStream(apiBase: string) {
  const [state, setState] = useState<SwarmState | null>(null);
  const [history, setHistory] = useState<Array<{ t: number; agents: number; edges: number; qps: number; lag: number }>>([]);
  const socketRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    const ws = new WebSocket(wsUrlFromHttp(apiBase));
    socketRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const parsed: SwarmState = JSON.parse(ev.data);
        setState(parsed);
        setHistory((h) => {
          const next = [...h, {
            t: parsed.ts,
            agents: parsed.agents.length,
            edges: parsed.edges.length,
            qps: parsed.cortex.embeddings_qps,
            lag: parsed.stream.lag_ms,
          }];
          return next.slice(Math.max(0, next.length - 200));
        });
      } catch {}
    };
    ws.onclose = () => { setTimeout(() => { if (socketRef.current === ws) socketRef.current = null; }, 1000); };
    return () => { ws.close(); };
  }, [apiBase]);
  return { state, history };
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl p-4 bg-black/60 backdrop-blur-md shadow-xl border border-indigo-700/40">
      <div className="text-indigo-300 text-sm mb-2">{title}</div>
      <div>{children}</div>
    </div>
  );
}
function NeonHeader() {
  return (
    <div className="mb-6">
      <h1 className="text-3xl md:text-4xl font-bold text-white">BrainSwarm <span className="text-indigo-400">Ops</span> Dashboard</h1>
      <p className="text-indigo-200/70 mt-1">Real-time swarm topology · Cortex metrics · Streams</p>
    </div>
  );
}
function formatUptime(u: number) {
  const h = Math.floor(u / 3600); const m = Math.floor((u % 3600) / 60); const s = u % 60;
  return `${h}h ${m}m ${s}s`;
}
function SwarmMiniMap({ agents, edges }: { agents: AgentStatus[]; edges: Edge[] }) {
  const layout = useMemo(() => {
    const cols = Math.ceil(Math.sqrt(Math.max(1, agents.length)));
    const pos: Record<string, { x: number; y: number }> = {};
    agents.forEach((a, i) => { const r = Math.floor(i / cols); const c = i % cols; pos[a.id] = { x: 80 + c * 140, y: 70 + r * 110 }; });
    return pos;
  }, [agents]);
  return (
    <svg className="w-full h-[320px] rounded-xl bg-gradient-to-b from-indigo-950 to-black border border-indigo-800/40">
      <g>
        {edges.map((e, i) => {
          const s = layout[e.source]; const t = layout[e.target]; if (!s || !t) return null;
          return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="currentColor" className="text-indigo-500/50" strokeWidth="2" />;
        })}
      </g>
      <g>
        {agents.map((a) => { const p = layout[a.id]; if (!p) return null;
          return (
            <g key={a.id}>
              <circle cx={p.x} cy={p.y} r={18} className={a.online ? "fill-green-400" : "fill-gray-500"} />
              <text x={p.x} y={p.y + 34} textAnchor="middle" className="fill-indigo-200 text-xs">{a.id}</text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export default function DashboardPage() {
  const apiBase =
    typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.host.replace(":3000", ":8001")}`
      : "http://localhost:8001";
  const { state, history } = useSwarmStream(apiBase);
  const agents = state?.agents ?? []; const edges = state?.edges ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-indigo-950 to-black p-6">
      <NeonHeader />
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <Card title="Agents Online">
          <div className="text-3xl font-semibold text-white">{agents.filter(a => a.online).length}</div>
          <div className="text-indigo-300 text-xs mt-1">Total: {agents.length}</div>
        </Card>
        <Card title="Edges">
          <div className="text-3xl font-semibold text-white">{edges.length}</div>
          <div className="text-indigo-300 text-xs mt-1">Relations</div>
        </Card>
        <Card title="Uptime">
          <div className="text-3xl font-semibold text-white">{formatUptime(state?.uptime_s ?? 0)}</div>
          <div className="text-indigo-300 text-xs mt-1">{new Date((state?.ts ?? 0) * 1000).toLocaleTimeString()}</div>
        </Card>
        <Card title="Cortex Mode">
          <div className="text-3xl font-semibold text-white">{state?.cortex?.mode ?? "—"}</div>
          <div className="text-indigo-300 text-xs mt-1">Interval: {state?.cortex?.summarizer_interval_s ?? 0}s</div>
        </Card>
        <Card title="Embeddings QPS">
          <div className="text-3xl font-semibold text-white">{(state?.cortex?.embeddings_qps ?? 0).toFixed(3)}</div>
          <div className="text-indigo-300 text-xs mt-1">Redis-derived</div>
        </Card>
        <Card title="Stream Lag">
          <div className="text-3xl font-semibold text-white">{state?.stream?.lag_ms ?? 0} ms</div>
          <div className="text-indigo-300 text-xs mt-1">Last event freshness</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <Card title="Activity (agents/edges)">
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history.map(h => ({ ...h, ts: new Date(h.t * 1000).toLocaleTimeString() }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ts" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="agents" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="edges" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Embeddings QPS">
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history.map(h => ({ ...h, ts: new Date(h.t * 1000).toLocaleTimeString() }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ts" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="qps" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Stream Lag (ms)">
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history.map(h => ({ ...h, ts: new Date(h.t * 1000).toLocaleTimeString() }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ts" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="lag" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <Card title="Swarm Topology">
          <SwarmMiniMap agents={agents} edges={edges} />
        </Card>
        <Card title="Summarizer">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-xl p-3 bg-black/50 border border-indigo-800/40">
              <div className="text-indigo-300 text-xs">Last Duration</div>
              <div className="text-white text-2xl">{(state?.cortex?.summarizer_last_ms ?? 0).toFixed(1)} ms</div>
            </div>
            <div className="rounded-xl p-3 bg-black/50 border border-indigo-800/40">
              <div className="text-indigo-300 text-xs">Last Status</div>
              <div className="text-white text-2xl">{state?.cortex?.summarizer_last_status ?? "unknown"}</div>
            </div>
            <div className="rounded-xl p-3 bg-black/50 border border-indigo-800/40">
              <div className="text-indigo-300 text-xs">Summary Stream</div>
              <div className="text-white text-2xl">{state?.stream?.summary_len ?? 0}</div>
            </div>
            <div className="rounded-xl p-3 bg-black/50 border border-indigo-800/40">
              <div className="text-indigo-300 text-xs">Embed Stream</div>
              <div className="text-white text-2xl">{state?.stream?.embed_len ?? 0}</div>
            </div>
          </div>
          <div className="text-indigo-300 text-xs mt-3">
            Redis: {state?.redis_connected ? "connected" : "not connected"}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 mt-6">
        <Card title="Agents">
          <div className="max-h-[340px] overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-indigo-300/80">
                  <th className="text-left font-medium py-1">ID</th>
                  <th className="text-left font-medium py-1">Kind</th>
                  <th className="text-left font-medium py-1">Online</th>
                  <th className="text-left font-medium py-1">CPU</th>
                  <th className="text-left font-medium py-1">Mem</th>
                  <th className="text-left font-medium py-1">Tasks</th>
                </tr>
              </thead>
              <tbody>
                {agents.map(a => (
                  <tr key={a.id} className="text-indigo-100/90">
                    <td className="py-1">{a.id}</td>
                    <td className="py-1">{a.kind}</td>
                    <td className="py-1">{a.online ? "✓" : "–"}</td>
                    <td className="py-1">{a.cpu.toFixed(1)}%</td>
                    <td className="py-1">{a.mem.toFixed(0)} MB</td>
                    <td className="py-1">{a.tasks_inflight}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}