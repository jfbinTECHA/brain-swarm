import IncidentPanel from "@/components/IncidentPanel";
// ... other imports

export default function Dashboard() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <SwarmGraph />
      <IncidentPanel />
    </div>
  );
}