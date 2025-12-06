import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import BpmnCard from "@/components/bpmn/BpmnCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type BpmnFile = {
  bpmn_id: number;
  filename: string;
  upload_date: string;
};

export default function ProjectBpmn() {
  const [projectBpmn, setProjectBpmn] = useState<BpmnFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { projectId } = useParams<{ projectId: string }>();

  useEffect(() => {
    const fetchProjectBpmn = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`/api/bpmn/get-bpmn-by-project/${projectId}`, {
          method: "GET",
          credentials: "include",
        });

        if (!res.ok) {
          throw new Error(`Failed to fetch most recent BPMN: ${res.status}`);
        }

        const data = await res.json();
        setProjectBpmn(data);
      } catch (error) {
        console.error("Error fetching BPMN:", error);
        setError(error instanceof Error ? error.message : "Failed to load BPMN");
      } finally {
        setLoading(false);
      }
    };

    if (projectId) fetchProjectBpmn();
  }, [projectId]);

  const handleDelete = (deleteId: number) => {
    setProjectBpmn((prev) => prev.filter((bpmn) => bpmn.bpmn_id !== deleteId));
  };

  if (loading) return <p className="p-8 text-center">Loading BPMN diagrams...</p>;
  if (error) return <p className="p-8 text-center text-red-500">Error: {error}</p>;

  return (
    <Card className="rounded-sm">
      <CardHeader>
        <CardTitle>BPMN Diagrams</CardTitle>
      </CardHeader>

      <CardContent>
        {projectBpmn.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 w-full mt-2">
            {projectBpmn.map((bpmn) => (
              <BpmnCard
                key={bpmn.bpmn_id}
                id={bpmn.bpmn_id}
                name={bpmn.filename}
                upload_date={bpmn.upload_date}
                onDelete={handleDelete}
                projectId={projectId} // NEW: so the existing View button adds ?projectId=...
              />
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-600 italic">
            You do not have any saved BPMN. Upload files and start process mining to create BPMN diagrams!
          </p>
        )}
      </CardContent>
    </Card>
  );
}
