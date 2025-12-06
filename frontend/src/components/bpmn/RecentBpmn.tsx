// src/components/bpmn/RecentBpmn.tsx
import { useEffect, useState } from "react";
import BpmnCard from "@/components/bpmn/BpmnCard";

type BpmnFile = {
  bpmn_id: number;
  filename: string;
  upload_date: string;
  project_id?: string | number; // include project context
};

export default function RecentBpmn() {
  const [latestBpmn, setLatestBpmn] = useState<BpmnFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecentBpmn = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch("/api/bpmn/recent");
        if (!res.ok) throw new Error(`Failed to fetch most recent BPMN: ${res.status}`);

        const data = await res.json();
        setLatestBpmn(data);
      } catch (err) {
        console.error("Error fetching BPMN:", err);
        setError(err instanceof Error ? err.message : "Failed to load BPMN");
      } finally {
        setLoading(false);
      }
    };

    fetchRecentBpmn();
  }, []);

  const handleDelete = (deleteId: number) => {
    setLatestBpmn((prev) => prev.filter((bpmn) => bpmn.bpmn_id !== deleteId));
  };

  if (loading) return <p className="p-8 text-center">Loading BPMN diagrams...</p>;
  if (error) return <p className="p-8 text-center text-red-500">Error: {error}</p>;

  return (
    <div>
      {latestBpmn.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 w-full mt-2">
          {latestBpmn.map((bpmn) => (
            <BpmnCard
              key={bpmn.bpmn_id}
              id={bpmn.bpmn_id}
              name={bpmn.filename}
              upload_date={bpmn.upload_date}
              onDelete={handleDelete}
              projectId={bpmn.project_id != null ? String(bpmn.project_id) : undefined}
            />
          ))}
        </div>
      ) : (
        <p className="text-center text-gray-500 italic">
          You do not have any saved BPMN. Start process mining to create BPMN diagrams!
        </p>
      )}
    </div>
  );
}
