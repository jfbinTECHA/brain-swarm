import { useEffect, useState } from "react";

type AdminEvent = {
  timestamp: string;
  action: string;
  result: string;
};

export default function AdminEvents() {
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const evtSource = new EventSource("http://localhost:8001/admin/events/stream");
    evtSource.onmessage = (e) => {
      try {
        const evt: AdminEvent = JSON.parse(e.data);
        setEvents((prev) => [evt, ...prev].slice(0, 10));
      } catch (err) {
        console.error("Bad event data", e.data);
      }
    };
    evtSource.onerror = (e) => {
      console.error("SSE connection lost", e);
      setError("⚠️ SSE stream disconnected; attempting reconnect...");
    };
    return () => evtSource.close();
  }, []);

  return (
    <section className="bg-[#121214] rounded-2xl p-6 border border-gray-800 shadow-glow">
      <h2 className="text-xl font-semibold text-teal-400 mb-4">
        🪵 Recent Admin Actions
      </h2>

      {error && <p className="text-red-500 mb-2">{error}</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-1">Timestamp (UTC)</th>
            <th className="text-left py-1">Action</th>
            <th className="text-left py-1">Result</th>
          </tr>
        </thead>
        <tbody>
          {events.length > 0 ? (
            events.map((evt, i) => (
              <tr key={i} className="border-b border-gray-800">
                <td className="py-1 text-gray-400">{evt.timestamp}</td>
                <td className="py-1">{evt.action}</td>
                <td
                  className={`py-1 ${
                    evt.result === "ok"
                      ? "text-green-400"
                      : "text-red-500 font-semibold"
                  }`}
                >
                  {evt.result}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={3} className="py-4 text-center text-gray-500">
                No admin events yet
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <p className="text-xs text-gray-500 mt-3">
        Live updates via Server-Sent Events (SSE)
      </p>
    </section>
  );
}