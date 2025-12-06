"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { ChevronDown, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function SavedRecommendationGroup({ savedRecs, onDelete}) {
  const [isOpen, setIsOpen] = useState(false);

  const boldLabels = (text: string) =>
  text
    .replace(/Recommendation:/g, "**Recommendation:**")
    .replace(/Rationale:/g, "**Rationale:**")
    .replace(/Implementation Steps:/g, "**Implementation Steps:**")
    .replace(/Expected Benefit:/g, "**Expected Benefit:**");

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border p-2 rounded-md">
      <div className="flex items-center justify-between cursor-pointer">
        <CollapsibleTrigger asChild>
          <Button variant="outline" className="w-full flex justify-between items-center">
            <span className="font-semibold text-lg">{savedRecs.length} Saved Recommendations</span>
            <ChevronDown className="w-5 h-5" />
          </Button>
        </CollapsibleTrigger>
      </div>

      <CollapsibleContent className="mt-2 space-y-2">
        {savedRecs.map((rec) => (
          <Card key={rec.recommendation_id}>
            <CardContent className="flex flex-row items-start justify-between">
              <div className="prose max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {boldLabels(rec.content)}
                </ReactMarkdown>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => onDelete(rec.recommendation_id)}
              >
              <Trash2 className="h-4 w-4" />
              <span className="sr-only">Delete recommendation</span>
              </Button>
            </CardContent>
          </Card>
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}
