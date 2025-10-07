import { useEffect, useState } from "react";
import SystemHealth from "../components/SystemHealth";
import AdminControls from "../components/AdminControls";

export default function Home() {
  const [meta, setMeta] = useState<string>("Loading...");

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001"}/gpt/meta`
        );
        const data = await res.json();
        setMeta(JSON.stringify(data, null, 2));
      } catch (err) {
        console.error("Failed to fetch meta:", err);
        setMeta("❌ Could not connect to backend");
      }
    }
    load();
  }, []);

  return (
    <main className="flex flex-col items-center justify-center p-8 space-y-6">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-teal-400 drop-shadow-glow">
          🧠 Brain Swarm Ops
        </h1>
        <p className="text-gray-400 mt-2">
          Secure AI Swarm Platform – Enterprise Control Panel
        </p>
      </div>

      <section className="w-full max-w-3xl bg-[#121214] rounded-2xl p-6 shadow-glow border border-gray-800">
        <h2 className="text-xl font-semibold text-teal-400 mb-3">
          API Connectivity Status
        </h2>
        <pre>{meta}</pre>
      </section>

      <SystemHealth />

      <AdminControls />

      <footer className="text-sm text-gray-600 pt-4">
        <p>© 2025 BrainSwarm Ops · Built by jfbinTECHA</p>
      </footer>
    </main>
  );
}