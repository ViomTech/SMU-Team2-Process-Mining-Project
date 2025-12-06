// frontend/src/components/ProcessMiner.tsx
// Context refs: After mining, it navigates to `/bpmn/view/:bpmnfile_id` :contentReference[oaicite:10]{index=10}; BPMN page needs projectId for fetching bottlenecks.
// Change: include `?projectId=...` in the redirect so the BPMN page can load the same top-10% bottlenecks immediately.
// WHY: Provides the missing context to the BPMN page without backend changes.

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function ProcessMiner({ onDone }: { onDone?: () => void }) {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const handleMergeAndMine = async () => {
    if (!projectId) return;

    setBusy(true);

    try {
      const mergeRes = await fetch(`/api/project/${projectId}/merge`, {
        method: "POST",
        credentials: "include",
      });

      const mergeBody = await mergeRes.json();
      if (!mergeRes.ok) throw new Error(mergeBody.error || "Merging failed");

      const mineRes = await fetch(`/api/process-mining/mine/${projectId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const mineBody = await mineRes.json();
      if (!mineRes.ok) throw new Error(mineBody.error || "Mining failed");

      toast.success("Process mined successfully!");
      // Include projectId so BPMN page can fetch top-10% bottlenecks immediately.
      navigate(`/bpmn/view/${mineBody.bpmnfile_id}?projectId=${projectId}`);

      if (onDone) onDone();

    } catch (err: any) {
      toast.error(err.message || "Unexpected error occurred.");

    } finally {
      setBusy(false);
    }
  };

  return (
    <Button onClick={handleMergeAndMine} disabled={busy}>
      {busy ? "Processing..." : "Mine Process"}
    </Button>
  );
}
