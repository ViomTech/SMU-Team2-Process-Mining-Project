// src/lib/monitoring.ts
export type ProcessOption = { project_id: number; project_name: string };

export async function fetchProcesses(): Promise<ProcessOption[]> {
  const res = await fetch("/api/monitoring/processes", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load processes");
  return res.json();
}

export type ActivityMetric = {
  activity: string; count: number;
  avg_seconds: number; median_seconds: number; p90_seconds: number;
  is_bottleneck: boolean;
};
export type TransitionMetric = {
  source_activity: string; target_activity: string; count: number;
  avg_seconds: number; median_seconds: number; p90_seconds: number;
  is_bottleneck: boolean;
};
export type MetricsPayload = {
  project_id: number; cases: number;
  activities: ActivityMetric[]; transitions: TransitionMetric[];
};

export async function fetchMetrics(projectId: number, start?: string, end?: string): Promise<MetricsPayload> {
  const params = new URLSearchParams();
  params.set("project_id", String(projectId));
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const res = await fetch(`/api/monitoring/metrics?${params.toString()}`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load metrics");
  return res.json();
}

// NEW: range
export type ProcessRange = { project_id: number; cases: number; min: string | null; max: string | null };
export async function fetchRange(projectId: number): Promise<ProcessRange> {
  const res = await fetch(`/api/monitoring/range?project_id=${projectId}`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load range");
  return res.json();
}
