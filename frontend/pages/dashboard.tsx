import IncidentPanel from "@/components/IncidentPanel";
// ... other imports

export default function Dashboard() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-zinc-900 p-4 rounded">
        <h2 className="text-xl font-semibold mb-4">Swarm Graph</h2>
        <p className="text-gray-400 mb-4">Real-time swarm visualization</p>
        <a href="http://localhost:8060" target="_blank" className="text-teal-400 hover:underline">
          Local Admin Console
        </a>
      </div>
      <IncidentPanel />
    </div>
  );
}