"use client";
import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { AlertTriangle, CheckCircle, Activity } from "lucide-react";
import { motion } from "framer-motion";

interface Incident {
  id: string;
  title: string;
  severity: string;
  status: string;
  created_at: number;
  resolved_at?: number;
}

export default function IncidentPanel() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  useEffect(() => {
    const ws = new WebSocket("wss://api.brainswarm.ai/ws/incidents");
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "incident_created") {
        setIncidents((p) => [msg.incident, ...p]);
      } else if (msg.type === "incident_resolved") {
        setIncidents((p) =>
          p.map((i) =>
            i.id === msg.incident.id ? { ...i, status: "resolved" } : i
          )
        );
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="grid gap-3">
      {incidents.map((i) => (
        <motion.div
          key={i.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card
            className={`${
              i.status === "resolved"
                ? "border-green-500/40"
                : "border-red-500/40 animate-pulse"
            } bg-zinc-900/40`}
          >
            <CardHeader className="flex justify-between">
              <span className="font-semibold">{i.title}</span>
              {i.status === "resolved" ? (
                <CheckCircle className="text-green-400" size={18} />
              ) : (
                <AlertTriangle className="text-red-400" size={18} />
              )}
            </CardHeader>
            <CardContent className="text-sm text-gray-300">
              <div>Severity: {i.severity}</div>
              <div>Status: {i.status}</div>
              <div>
                Started: {new Date(i.created_at * 1000).toLocaleString()}
              </div>
              {i.resolved_at && (
                <div>
                  Resolved: {new Date(i.resolved_at * 1000).toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}