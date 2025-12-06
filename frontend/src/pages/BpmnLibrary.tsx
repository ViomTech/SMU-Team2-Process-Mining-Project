import { useState, useEffect } from "react";
import BpmnCard from "@/components/bpmn/BpmnCard";

type BpmnFile = {
  bpmn_id: number,
  filename: string,
  upload_date: string
}

export default function BpmnLibrary() {
  const [allBpmn, setAllBpmn] = useState<BpmnFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAllBpmn = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch("/api/bpmn/all-bpmn", {
          method: "GET",
          credentials: "include"
        });

        if (!res.ok) {
          throw new Error(`Failed to fetch most recent BPMN: ${res.status}`);
        }
        
        const data = await res.json();
        setAllBpmn(data);

      } catch (error) {
        console.error('Error fetching BPMN:', error);
        setError(error instanceof Error ? error.message : 'Failed to load BPMN');

      } finally {
        setLoading(false);
      }
    }

    fetchAllBpmn();
  }, []);

  if (loading) return <div className="p-8 text-center">Loading Projects...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  return (
    <div className="p-4 md:p-8">
      <p className="text-2xl font-semibold">My Processes / Saved BPMN</p>

      <div className="mt-8">
        <div className="flex flex-row flex-wrap gap-4 justify-start">
          {allBpmn.length > 0 ? (
            allBpmn.map((bpmn) => (
              <BpmnCard id={bpmn.bpmn_id} name={bpmn.filename} upload_date={bpmn.upload_date} />
            ))
          ) : (
            <p className="text-center">You do not have any saved BPMN. Start process mining or upload your own BPMN diagrams!</p>
          )}
        </div>
      </div>
    </div>
  )
}