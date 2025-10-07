import SystemHealth from "../../components/SystemHealth";
import AdminControls from "../../components/AdminControls";
import AdminEvents from "../../components/AdminEvents";
import ToastManager from "../../components/ToastManager";
import LiveOpsIndicator from "../../components/LiveOpsIndicator";

export default function AdminDashboard() {
  return (
    <main className="p-8 space-y-8 bg-graphite min-h-screen text-gray-100">
      {/* Header */}
      <div className="flex flex-col items-center justify-center space-y-2">
        <h1 className="text-3xl font-bold text-teal-400 drop-shadow-glow text-center">
          🧠 BrainSwarmOps Admin Console
        </h1>
        <p className="text-gray-400 text-center">
          Unified system health, control, and live ops telemetry
        </p>
        <div className="pt-2">
          <LiveOpsIndicator />
        </div>
      </div>

      {/* System Panels */}
      <div className="grid gap-8 md:grid-cols-2">
        <SystemHealth />
        <AdminControls />
      </div>

      {/* Event Feed */}
      <AdminEvents />

      {/* Toast Notifications */}
      <ToastManager streamUrl="http://localhost:8001/admin/events/stream" />
    </main>
  );
}