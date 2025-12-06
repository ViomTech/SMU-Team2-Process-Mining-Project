import { useState, useEffect, useRef } from "react";
import { SavedRecommendationGroup } from "@/components/SavedRecommendation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Bookmark, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface BottleneckData {
  process_name: string;
  activity_name: string;
  metrics: {
    "90th Percentile Duration"?: string;
    "Occurrences"?: number;
  };
}

interface BottleneckAnalysisProps {
  bottleneckData: BottleneckData | null;
  projectId: string | undefined;
}

interface SavedRecommendation {
  recommendation_id: string;
  content: string;
  bottleneck_activity: string;
  project_id?: string;
  project_name?: string;
}

export default function Recommendation({
  bottleneckData,
  projectId,
}: BottleneckAnalysisProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [savedRecs, setSavedRecs] = useState<SavedRecommendation[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToChatBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    scrollToChatBottom();
  }, [messages]);

  // --- API Handlers ---
  const handleGenerateRecommendations = async () => {
    if (!bottleneckData) return;

    setIsLoading(true);

    const initialUserPrompt = `
      You are an expert Business Process Optimization (BPO) consultant specializing in analyzing BPMN models and identifying actionable solutions for process bottlenecks. Your task is to analyze the provided bottleneck data and generate three distinct, actionable recommendations.
      For each recommendation, clearly explain *why* this change would improve the process, using the provided metrics as evidence.
      For each recommendation, Use this exact format:

      [[RECOMMENDATION]]
      Recommendation: <title>
      Rationale: <why>
      Implementation Steps:
      - Step 1
      - Step 2
      - Add more steps if needed
      Expected Benefit: <benefits>
      [[END_RECOMMENDATION]]

      Keep your entire response concise and to the point.
      Process Name: ${bottleneckData.process_name}
      Activity: '${bottleneckData.activity_name}'
      Metrics:
        - 90th Percentile Duration: ${bottleneckData.metrics["90th Percentile Duration"]}
        - Occurrences: ${bottleneckData.metrics["Occurrences"]}
    `;

    const initialMessages: Message[] = [
      {
        role: "system",
        content:
          "You are an expert Business Process Optimization (BPO) consultant specializing in analyzing BPMN models and identifying actionable solutions for process bottlenecks",
      },
      { role: "user", content: initialUserPrompt },
    ];

    try {
      const response = await fetch("/api/recommendation/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: initialMessages }),
      });
      const data = await response.json();

      setMessages([
        ...initialMessages,
        { role: "assistant", content: data.answer },
      ]);
    } catch (err: any) {
      console.error("Failed to fetch initial recommendations:", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Follow-up handler ---
  const handleFollowUpSubmit = async () => {
    if (!userInput.trim()) return;

    setIsLoading(true);
    const newMessages: Message[] = [...messages, { role: "user", content: userInput }];
    setMessages(newMessages);
    setUserInput("");

    try {
      const response = await fetch("/api/recommendation/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages }),
      });
      const data = await response.json();

      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err: any) {
      console.error("Failed to fetch follow-up:", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Save recommendation ---
  const handleSaveRecommendation = async (content: string) => {
    if (!bottleneckData || !projectId) {
      toast.error("Cannot save recommendation: Missing project context.");
      return;
    }

    toast.info("Saving recommendation to library...");

    try {
      const response = await fetch("/api/recommendation/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          content,
          bottleneck_activity: bottleneckData.activity_name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save.");
      }

      const newSavedRecData = await response.json();

      const newSavedRec: SavedRecommendation = {
        recommendation_id: newSavedRecData.recommendation_id,
        content,
        bottleneck_activity: bottleneckData.activity_name,
        project_id: projectId,
      };

      setSavedRecs((prevRecs) => [...prevRecs, newSavedRec]);
      toast.success("Recommendation saved successfully!");
    } catch (err: any) {
      console.error("Save failed:", err.message);
      toast.error("Could not save recommendation.");
    }
  };

  const handleDeleteRecommendation = async (recommendationId: string) => {
    if (!confirm("Are you sure you want to delete this recommendation?")) return;

    try {
      const response = await fetch("/api/recommendation/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recommendation_id: recommendationId }),
      });

      if (!response.ok) throw new Error("Failed to delete recommendation.");

      setSavedRecs((prevRecs) =>
        prevRecs.filter((rec) => rec.recommendation_id !== recommendationId)
      );

      toast.success("Recommendation deleted.");
    } catch (err: any) {
      console.error("Delete failed:", err.message);
      toast.error("Could not delete recommendation.");
    }
  };

  useEffect(() => {
    if (!projectId || !bottleneckData) return;

    const fetchSaved = async () => {
      try {
        const url = `/api/recommendation/library?project_id=${projectId}`;
        const res = await fetch(url, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to fetch saved recommendations");
        const data: SavedRecommendation[] = await res.json();

        const filtered = data.filter(
          (rec) => rec.bottleneck_activity === bottleneckData.activity_name
        );
        setSavedRecs(filtered);
      } catch (err: any) {
        console.error("Error fetching saved recommendations:", err.message);
      }
    };

    fetchSaved();
  }, [projectId, bottleneckData]);

  return (
    <div className="space-y-8">
      {/* --- Bottleneck Info --- */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{bottleneckData?.process_name}</CardTitle>
            <CardDescription>
              Bottleneck Identified:{" "}
              <span className="font-semibold text-blue-600">
                {bottleneckData?.activity_name}
              </span>
            </CardDescription>
          </div>

          {messages.length === 0 && (
            <Button onClick={handleGenerateRecommendations} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              Get AI Recommendations
            </Button>
          )}
        </CardHeader>

        <CardContent>
          <p className="font-medium text-muted-foreground mb-2">Key Metrics</p>
          <ul className="list-disc list-inside space-y-1">
            {Object.entries(bottleneckData?.metrics || {}).map(([key, value]) => (
              <li key={key}>
                <span className="font-semibold">{key}:</span> {String(value)}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* --- Chatbot Container --- */}
      {messages.length > 0 && (
          <div 
            ref={chatContainerRef}
            className="border rounded-lg p-4 bg-muted/20 max-h-[70vh] overflow-y-auto space-y-4"
          >
          {messages.map((msg, index) => {
            if (msg.role === "system" || (msg.role === "user" && index === 1)) return null;

            if (msg.role === "assistant") {
              if (index === 2) {
                // First response with 3 separate recommendations
                const recs = msg.content
                  .split("[[RECOMMENDATION]]")
                  .map((r) => r.replace("[[END_RECOMMENDATION]]", "").trim())
                  .filter((r) => r);

                const boldLabels = (text: string) =>
                    text
                    .replace(/Recommendation:/g, "**Recommendation:**")
                    .replace(/Rationale:/g, "**Rationale:**")
                    .replace(/Implementation Steps:/g, "**Implementation Steps:**")
                    .replace(/Expected Benefit:/g, "**Expected Benefit:**");

                return (
                  <div key={index} className="space-y-4">
                    {recs.map((rec, recIndex) => (
                      <div
                        key={recIndex}
                        className="bg-muted border rounded-lg p-4"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <p className="font-semibold text-foreground/80">
                            Recommendation #{recIndex + 1}
                          </p>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleSaveRecommendation(rec)}
                          >
                            <Bookmark className="h-5 w-5" />
                          </Button>
                        </div>
                        <div className="prose text-sm max-w-none dark:prose-invert">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {boldLabels(rec)}
                            </ReactMarkdown>
                        </div>
                      </div>
                    ))}
                  </div>
                );
              }

              return (
                <div key={index} className="text-foreground prose dark:prose-invert max-w-none text-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                    </ReactMarkdown>
                </div>
              );
            }

            if (msg.role === "user") {
              return (
                <div key={index} className="flex justify-end">
                  <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg max-w-[80%] text-sm">
                    {msg.content}
                  </div>
                </div>
              );
            }

            return null;
          })}
          
          {isLoading && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating response...
          </div>
          )}

          <div ref={chatEndRef} />
        </div>
      )}

      {/* --- Follow-up Input --- */}
      {messages.length > 0 && (
        <div className="border rounded-lg p-4 bg-muted/20 max-h-[70vh] overflow-y-auto space-y-4">
            <div className="w-full flex items-end gap-1 border border-border rounded-2xl p-3 bg-background shadow-sm">
                <Textarea
                placeholder="Ask a follow-up question"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleFollowUpSubmit();
                    }
                }}
                className="flex-1 resize-none border-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm bg-transparent"
                rows={1}
                />
                <Button
                onClick={handleFollowUpSubmit}
                disabled={!userInput.trim()}
                className="rounded-full px-4 py-2 text-sm"
                >
                Send
                </Button>
            </div>
            <div>
                <p className="text-xs text-muted-foreground text-center">
                    * AI can make mistakes, so double-check it.
                </p>
            </div>
        </div>
      )}

      {/* --- Saved Recommendations Section --- */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Saved Recommendations</h2>
        {savedRecs.length === 0 ? (
          <div className="text-center text-muted-foreground border rounded-lg p-6">
            <p>No saved recommendations yet.</p>
          </div>
        ) : (
          <SavedRecommendationGroup
            savedRecs={savedRecs}
            onDelete={handleDeleteRecommendation}
          />
        )}
      </div>
    </div>
  );
}
