// frontend/src/components/ProjectRecommendation.tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronRight } from "lucide-react";
import { fetchBottlenecks, type BottleneckMetric, makeRecommendationPath } from "@/lib/bottlenecks";
import { formatDurationSec } from "@/lib/time"; // NEW

export default function ProjectRecommendation() {
  const [bottlenecks, setBottlenecks] = useState<BottleneckMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { projectId } = useParams<{ projectId: string }>();

  useEffect(() => {
    const load = async () => {
      if (!projectId) return;
      try {
        setLoading(true);
        const data = await fetchBottlenecks(projectId);
        setBottlenecks(data);
      } catch (e: any) {
        setError(e.message || "Failed to fetch bottleneck data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  if (loading) return <div className="p-8 text-center">Loading bottlenecks.</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
  if (!bottlenecks.length) return <div className="p-8 text-center text-muted-foreground">No significant bottlenecks detected (Top 10%).</div>;

  return (
    <Card className="rounded-sm mt-4">
      <CardHeader><CardTitle>Top 10% Bottlenecks</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-2">
          {bottlenecks.map((bn) => {
            const path = projectId ? makeRecommendationPath(projectId, bn) : "#";
            const title =
              bn.kind === "activity"
                ? `Activity: ${(bn as any).activity}`
                : `Transition: ${(bn as any).source_activity} → ${(bn as any).target_activity}`;

            return (
              <Link
                to={path}
                state={{ bottleneck: bn }}
                key={`${bn.kind}-${bn.id}`}
                className="flex items-center justify-between p-4 border rounded-md hover:bg-red-50 transition-colors"
              >
                <div className="flex flex-col">
                  <span className="font-semibold text-red-700">{title}</span>
                  <span className="text-sm text-muted-foreground">
                    90th percentile duration: {formatDurationSec(bn.p90_seconds)} · Occurrences: {bn.count}
                  </span>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              </Link>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
