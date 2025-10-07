import { useEffect, useState } from "react";

type ServiceStatus = {
  name: string;
  url?: string;
  status: string;
  message: string;
};

const services: Omit<ServiceStatus, "status" | "message">[] = [
  { name: "API", url: "http://localhost:8001/healthz" },
  { name: "Frontend", url: "http://localhost:3000" },
  { name: "Postgres" },
  { name: "Redis" },
];

export default function SystemHealth() {
  const [statuses, setStatuses] = useState<ServiceStatus[]>([]);

  async function checkHealth() {
    const checks = await Promise.all(
      services.map(async (svc) => {
        try {
          if (!svc.url) {
            return { ...svc, status: "warn", message: "Internal check only" };
          }
          const res = await fetch(svc.url);
          if (res.ok) return { ...svc, status: "ok", message: "Healthy" };
          return { ...svc, status: "warn", message: `HTTP ${res.status}` };
        } catch {
          return { ...svc, status: "error", message: "Unreachable" };
        }
      })
    );
    setStatuses(checks);
  }

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const color = (s: ServiceStatus["status"]) =>
    s === "ok"
      ? "text-green-400"
      : s === "warn"
      ? "text-yellow-400"
      : "text-red-500";

  return (
    <section className="bg-[#121214] rounded-2xl p-6 border border-gray-800 shadow-glow">
      <h2 className="text-xl font-semibold text-teal-400 mb-4">
        🩺 System Health Monitor
      </h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-1">Service</th>
            <th className="text-left py-1">Status</th>
            <th className="text-left py-1">Message</th>
          </tr>
        </thead>
        <tbody>
          {statuses.map((svc) => (
            <tr key={svc.name} className="border-b border-gray-800">
              <td className="py-2">{svc.name}</td>
              <td className={`py-2 ${color(svc.status)}`}>
                {svc.status.toUpperCase()}
              </td>
              <td className="py-2 text-gray-300">{svc.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}