import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export type Toast = {
  id: string;
  message: string;
  type: "success" | "error" | "warning";
};

export default function ToastManager({ streamUrl }: { streamUrl: string }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const evtSource = new EventSource(streamUrl);

    evtSource.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data);
        const type =
          evt.result === "ok"
            ? "success"
            : evt.result === "error"
            ? "error"
            : "warning";

        const toast: Toast = {
          id: Math.random().toString(36).substring(2, 10),
          message: `🧠 ${evt.action.toUpperCase()} — ${evt.result.toUpperCase()}`,
          type,
        };
        setToasts((prev) => [toast, ...prev].slice(0, 5));

        // Auto-dismiss after 5s
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== toast.id));
        }, 5000);
      } catch (err) {
        console.error("Bad SSE data for toast", e.data);
      }
    };

    evtSource.onerror = () => {
      console.warn("⚠️ SSE toast connection lost; retrying...");
    };

    return () => evtSource.close();
  }, [streamUrl]);

  return (
    <div className="fixed bottom-6 right-6 space-y-2 z-50">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className={`backdrop-blur-md border border-gray-700/40 text-sm
              px-4 py-3 rounded-xl shadow-lg shadow-black/30
              flex items-center gap-2 transition-all duration-500
              ${
                t.type === "success"
                  ? "bg-teal-500/30 text-teal-200 ring-1 ring-teal-400/30"
                  : t.type === "error"
                  ? "bg-red-600/30 text-red-300 ring-1 ring-red-400/30"
                  : "bg-yellow-500/20 text-yellow-200 ring-1 ring-yellow-400/20"
              }`}
          >
            <span className="text-lg leading-none">
              {t.type === "success"
                ? "✅"
                : t.type === "error"
                ? "❌"
                : "⚠️"}
            </span>
            <span className="font-medium tracking-wide">{t.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}