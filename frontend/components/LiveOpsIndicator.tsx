import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export default function LiveOpsIndicator() {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const evtSource = new EventSource("http://localhost:8001/admin/events/stream");

    evtSource.onmessage = () => {
      setActive(true);
      setTimeout(() => setActive(false), 3000);
    };

    evtSource.onerror = () => {
      console.warn("⚠️ Lost LiveOps connection, retrying...");
    };

    return () => evtSource.close();
  }, []);

  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <motion.div
        animate={{
          scale: active ? [1, 1.5, 1] : 1,
          opacity: active ? [0.8, 1, 0.8] : 0.5,
        }}
        transition={{ duration: 1.2, repeat: active ? Infinity : 0 }}
        className={`w-3 h-3 rounded-full ${
          active ? "bg-teal-400 shadow-glow" : "bg-gray-600"
        }`}
      />
      <span className={active ? "text-teal-400" : "text-gray-500"}>
        {active ? "Live Ops Active" : "Listening..."}
      </span>
    </div>
  );
}