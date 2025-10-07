import { useState } from "react";

export default function AdminControls() {
  const [status, setStatus] = useState<string>("");

  const sendCommand = async (endpoint: string, action: string) => {
    if (!confirm(`Are you sure you want to ${action} the BrainSwarmOps stack?`))
      return;
    setStatus(`Sending ${action} command...`);
    try {
      const res = await fetch(`http://localhost:8001/admin/${endpoint}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.status === "ok") {
        setStatus(`✅ ${action} successful.`);
      } else {
        setStatus(
          `⚠️ Error during ${action}: ${data.stderr || data.message || "Unknown"}`
        );
      }
    } catch (err: any) {
      setStatus(`❌ ${action} request failed: ${err.message}`);
    }
  };

  return (
    <section className="bg-[#121214] rounded-2xl p-6 border border-gray-800 shadow-glow">
      <h2 className="text-xl font-semibold text-teal-400 mb-4">
        🧭 System Control Panel
      </h2>
      <p className="text-gray-400 mb-3">
        Use these controls to remotely manage all BrainSwarmOps containers.
      </p>

      <div className="flex flex-wrap gap-4">
        <button
          onClick={() => sendCommand("shutdown", "shut down")}
          className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium shadow-md"
        >
          🛑 Shut Down Stack
        </button>

        <button
          onClick={() => sendCommand("restart", "restart")}
          className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-medium shadow-md"
        >
          🔁 Restart Stack
        </button>
      </div>

      {status && <p className="text-sm text-gray-300 mt-3">{status}</p>}
    </section>
  );
}