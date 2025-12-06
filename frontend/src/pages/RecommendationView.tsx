// src/pages/RecommendationDetailPage.tsx
import { useEffect, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import Recommendation from '@/components/Recommendation';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatDurationSec } from '@/lib/time'; // NEW
import { fetchBottlenecks, type BottleneckMetric } from "@/lib/bottlenecks";
import { getProjectById } from "@/lib/api";

type DrillRow = { case_id: string; from: string; to: string | null; seconds: number | null; };

export default function RecommendationDetailPage() {
  const { projectId, bottleneckId } = useParams<{ projectId: string, bottleneckId: string }>();
  const [loading, setLoading] = useState(true);
  const [meta, setMeta] = useState<{ process_name: string; activity_name: string; metrics: Record<string, any> } | null>(null);
  const [drill, setDrill] = useState<DrillRow[]>([]);
  const [bottleneckDetails, setBottleneckDetails] = useState<BottleneckMetric | null>(null);
  const [projectName, setProjectName] = useState<BottleneckMetric | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
      const loadAllData = async () => {
          if (!projectId || !bottleneckId) return;
          setLoading(true);
          setError(null);
          
          try {
              const projectDetails = await getProjectById(projectId);
              setProjectName(projectDetails.project_name);

              const allBottlenecks = await fetchBottlenecks(projectId); 
              const decodedId = decodeURIComponent(bottleneckId); // e.g., "activity:Manual Underwriting"
              
              // Find the bottleneck based on the decoded ID
              // This logic might need adjustment based on how 'id' is structured in BottleneckMetric
              const targetBottleneck = allBottlenecks.find(bn => {
                  if (decodedId.startsWith("activity:") && bn.kind === 'activity') {
                      return `activity:${(bn as any).activity}` === decodedId;
                  }
                  if (decodedId.startsWith("transition:") && bn.kind === 'transition') {
                        return `transition:${(bn as any).source_activity}-->${(bn as any).target_activity}` === decodedId;
                  }
                  return false;
              });

              if (!targetBottleneck) throw new Error("Bottleneck details not found.");
              setBottleneckDetails(targetBottleneck); // Set the state with metrics!

              // --- Fetch 2: Get Drilldown Data ---
              // Construct query string based on the found bottleneck
              let qs = "";
              if (targetBottleneck.kind === "activity") {
                  qs = `kind=activity&activity=${encodeURIComponent((targetBottleneck as any).activity)}`;
              } else {
                    qs = `kind=transition&source_activity=${encodeURIComponent((targetBottleneck as any).source_activity)}&target_activity=${encodeURIComponent((targetBottleneck as any).target_activity)}`;
              }
              const drillRes = await fetch(`/api/process-mining/bottlenecks/${projectId}/drilldown?${qs}`, { credentials: "include" });
              if (!drillRes.ok) throw new Error("Failed to fetch drilldown data.");
              const drillData: DrillRow[] = await drillRes.json();
              setDrill(drillData);

          } catch(err: any) {
              setError(err.message);
              console.error("Error loading detail page:", err);
          } finally {
              setLoading(false);
          }
      };
      loadAllData();
  }, [projectId, bottleneckId]);

  const adaptedBottleneckData = bottleneckDetails ? {
    process_name: projectName,
    activity_name: bottleneckDetails.kind === 'activity' ? (bottleneckDetails as any).activity : `${(bottleneckDetails as any).source_activity} → ${(bottleneckDetails as any).target_activity}`,
    metrics: { // Now we populate metrics correctly!
        "90th Percentile Duration": formatDurationSec(bottleneckDetails.p90_seconds),
        "Occurrences": bottleneckDetails.count,
    }
  } : null;

  return (
    <div className="page mt-4 px-8">
      <header className="mb-8 flex items-center gap-4">
        <Link to={`/projects/${projectId}`}><Button><ArrowLeft /></Button></Link>
        <div>
          <h1 className="text-3xl font-bold">AI Analysis</h1>
        </div>
      </header>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (<Recommendation bottleneckData={adaptedBottleneckData} projectId={projectId} />)}

      {/* simple drilldown table under the AI card */}
      {!loading && drill.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-2">Contributing Cases</h2>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="p-2 text-left">Case</th>
                  <th className="p-2 text-left">From</th>
                  <th className="p-2 text-left">To</th>
                  <th className="p-2 text-left">Duration</th>
                </tr>
              </thead>
              <tbody>
                {drill.map((r, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2">{r.case_id}</td>
                    <td className="p-2">{r.from}</td>
                    <td className="p-2">{r.to ?? "-"}</td>
                    <td className="p-2">{formatDurationSec(r.seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
