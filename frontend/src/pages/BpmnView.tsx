// src/pages/BpmnView.tsx
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
// --- Import useAuth ---
import { useAuth } from "@/contexts/AuthContext";
// --- End Imports ---
import BpmnEditor from "@/components/bpmn/BpmnEditor";
import { fetchBottlenecks } from "../lib/bottlenecks";
import type { BottleneckMetric } from "../lib/bottlenecks";

export default function BpmnView() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  // --- Get user AND isLoading state ---
  const { user, loading: isAuthLoading } = useAuth(); // Use 'loading' from context

  const projectIdFromUrl = useMemo(() => searchParams.get("projectId") ?? "", [searchParams]);
  const [resolvedProjectId, setResolvedProjectId] = useState<string>(projectIdFromUrl);
  const [bns, setBns] = useState<BottleneckMetric[]>([]);
  const [loadingBns, setLoadingBns] = useState(false); // Renamed state

  // Resolve projectId if missing
  useEffect(() => {
    let cancelled = false;
    const resolveProjectId = async () => {
      if (!id) return;
      if (projectIdFromUrl) {
        setResolvedProjectId(projectIdFromUrl);
        return;
      }
      try {
        const res = await fetch(`/api/bpmn/get-info/${id}`, { credentials: "include" });
        if (!res.ok) throw new Error(`Failed to fetch BPMN info: ${res.status}`);
        const info = await res.json();
        const pid = info.project_id != null ? String(info.project_id) : "";
        if (!cancelled && pid) {
          setResolvedProjectId(pid);
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.set("projectId", pid);
            return next;
          }, { replace: true });
        }
      } catch (err) {
        console.error("Failed to resolve project ID:", err);
        setResolvedProjectId("");
      }
    };
    resolveProjectId();
    return () => { cancelled = true; };
  }, [id, projectIdFromUrl, setSearchParams]);

  // Load bottlenecks when we have a project
  useEffect(() => {
    if (!id || !resolvedProjectId) return;
    const run = async () => {
      setLoadingBns(true);
      try {
        const data = await fetchBottlenecks(resolvedProjectId);
        setBns(data);
      } catch (err) {
        console.error("Failed to fetch bottlenecks:", err);
        setBns([]);
      } finally {
        setLoadingBns(false);
      }
    };
    run();
  }, [id, resolvedProjectId]);

  // --- Wait for Authentication to Load ---
  if (isAuthLoading) {
    return <div className="p-4 text-center">Loading user information...</div>;
  }
  // --- End Loading Check ---

  // Main component render
  return (
    // Keep the original layout with mx-6
    <div className="flex flex-col h-[calc(100vh-4rem)] mx-6">
      {/* Container for the BPMN Editor */}
      <div className="flex-1 min-h-0 w-full overflow-hidden rounded border">
        {id ? ( // Render editor only if ID exists
          <BpmnEditor
            id={Number(id)}
            projectId={resolvedProjectId || undefined}
            highlights={resolvedProjectId ? bns : []}
            // --- Pass the user role down ---
            userRole={user?.role}
          />
        ) : (
          <div className="p-4 text-center text-muted-foreground">Invalid BPMN ID.</div>
        )}
      </div>
    </div>
  );
}