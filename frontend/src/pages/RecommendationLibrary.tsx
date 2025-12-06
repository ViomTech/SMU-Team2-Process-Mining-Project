// src/pages/RecommendationLibrary.tsx
import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { getRecommendation, deleteRecommendation } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

interface Recommendation {
  recommendation_id: string;
  content: string;
  bottleneck_activity: string;
  project_id?: string;
  project_name: string;
}

const boldLabels = (text: string) =>
  text
    .replace(/Recommendation:/g, "**Recommendation:**")
    .replace(/Rationale:/g, "**Rationale:**")
    .replace(/Implementation Steps:/g, "**Implementation Steps:**")
    .replace(/Expected Benefit:/g, "**Expected Benefit:**");

export default function RecommendationLibrary() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async (recommendationId: string) => {
    if (!window.confirm("Are you sure you want to delete this recommendation?")) {
      return;
    }
    try {
      await deleteRecommendation(recommendationId);
      setRecs(prevRecs =>
        prevRecs.filter(rec => rec.recommendation_id !== recommendationId)
      );
      toast.success("Recommendation deleted successfully!");
    } catch (err: any) {
      console.error("Failed to delete recommendation:", err);
      toast.error(err.message || "Could not delete the recommendation.");
    }
  };

  useEffect(() => {
    getRecommendation()
      .then((data) => setRecs(data))
      .catch((err) => setError(err.message || "Failed to load recommendations"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-center">Loading recommendations...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  return (
    <div className="p-4 md:p-8">
      <p className="text-2xl font-semibold">Saved Recommendations</p>
      
      <div className="mt-8">
        {recs.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {recs.map((rec) => (
              <Card
                key={rec.recommendation_id}
                className="hover:shadow-lg transition-shadow duration-200 flex flex-col h-full"
              >
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-lg">{rec.project_name}</CardTitle>
                    <CardDescription className="line-clamp-1 text-sm text-gray-500">
                      Bottleneck: {rec.bottleneck_activity}
                    </CardDescription>
                    <CardDescription className="line-clamp-2">
                      {rec.content.split("\n")[0]}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive flex-shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(rec.recommendation_id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                    <span className="sr-only">Delete recommendation</span>
                  </Button>
                </CardHeader>
                <CardContent className="flex-grow">
                  <div className="prose max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {boldLabels(rec.content)}
                    </ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p>You do not have any saved recommendations.</p>
        )}
      </div>
    </div>
  );
}