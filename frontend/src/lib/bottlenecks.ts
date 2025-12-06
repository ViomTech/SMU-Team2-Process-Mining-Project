// frontend/src/lib/bottlenecks.ts
// Centralizes bottleneck types, fetching, and deep-link construction.
// Used by ProjectRecommendation, FilesDashboard, and BpmnEditor.

// ---- Types (mirror backend response shape) ----
export type BNBase = {
  id: number;
  kind: "activity" | "transition";
  count: number;
  avg_seconds: number | null;
  median_seconds: number | null;
  p90_seconds: number | null;
  is_bottleneck: boolean;
  bpmn_element_id?: string | null;
};

export type ActivityBN = BNBase & { activity: string };
export type TransitionBN = BNBase & {
  source_activity: string;
  target_activity: string;
};

export type BottleneckMetric = ActivityBN | TransitionBN;

// ---- Fetch top-10% bottlenecks for a project ----
export async function fetchBottlenecks(projectId: string): Promise<BottleneckMetric[]> {
  const res = await fetch(`/api/process-mining/bottlenecks/${projectId}`, {
    credentials: "include",
  });
  if (!res.ok) {
    let msg = "Failed to fetch bottlenecks";
    try {
      const body = await res.json();
      if (body?.error) msg = body.error;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// ---- Build the canonical Recommendations route used across the app ----
export function makeRecommendationPath(projectId: string, bn: BottleneckMetric): string {
  if (bn.kind === "activity") {
    const id = `activity:${(bn as ActivityBN).activity}`;
    return `/projects/${projectId}/recommendation/${encodeURIComponent(id)}`;
  }
  const t = bn as TransitionBN;
  const id = `transition:${t.source_activity}-->${t.target_activity}`;
  return `/projects/${projectId}/recommendation/${encodeURIComponent(id)}`;
}

// ---- Variant that accepts raw parts (for clicks from overlays) ----
export function makeRecommendationPathFromParts(
  projectId: string,
  kind: "activity" | "transition",
  activity?: string,
  source_activity?: string,
  target_activity?: string
): string {
  if (kind === "activity" && activity) {
    return `/projects/${projectId}/recommendation/${encodeURIComponent(`activity:${activity}`)}`;
  }
  if (kind === "transition" && source_activity && target_activity) {
    return `/projects/${projectId}/recommendation/${encodeURIComponent(`transition:${source_activity}-->${target_activity}`)}`;
  }
  throw new Error("Invalid recommendation link params");
}


