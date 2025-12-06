// src/pages/MetricsDashboard.tsx
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchProcesses,
  fetchMetrics,
  fetchRange,
  type ProcessOption,
  type MetricsPayload,
  type ProcessRange,
} from "@/lib/monitoring";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { format } from "date-fns";

// --- helpers ---
function toIsoUtc(value?: string): string | undefined {
  if (!value) return undefined;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

// Convert seconds → "Xh Ym"
function toHrsMins(s?: number) {
  if (s == null) return "-";
  const totalMin = Math.round(s / 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h <= 0) return `${m}m`;
  return `${h}h ${m}m`;
}

// Severity color scale: light gray → dark gray by P90; red if bottleneck
function severityColor(p90: number, p90Min: number, p90Max: number, isBottleneck?: boolean) {
  if (isBottleneck) return "#ef4444"; // accent for bottlenecks
  if (!Number.isFinite(p90Min) || !Number.isFinite(p90Max) || p90Max <= p90Min) return "#9ca3af";
  const t = Math.max(0, Math.min(1, (p90 - p90Min) / (p90Max - p90Min))); // 0..1
  const lerp = (a: number, b: number, u: number) => Math.round(a + (b - a) * u);
  const from = { r: 229, g: 231, b: 235 };
  const to = { r: 17, g: 24, b: 39 };
  const r = lerp(from.r, to.r, t);
  const g = lerp(from.g, to.g, t);
  const b = lerp(from.b, to.b, t);
  return `rgb(${r}, ${g}, ${b})`;
}

// ---- Custom tooltips (show count and % of cases; no red "Bottleneck" label) ----
function ActivityTooltip({ active, payload, totalCases }: any) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  const pct = totalCases ? Math.round((p.count / totalCases) * 1000) / 10 : 0; // 1 decimal
  return (
    <div className="rounded-md border bg-white p-3 text-xs shadow">
      <div className="mb-1 font-medium">Activity: {p.name}</div>
      <div>Typical worst-case (P90): {toHrsMins(p.p90)}</div>
      <div>Median: {toHrsMins(p.median)}</div>
      <div>Average: {toHrsMins(p.avg)}</div>
      <div className="mt-1">Count: {p.count} ({pct}% of cases)</div>
    </div>
  );
}

function TransitionTooltip({ active, payload, totalCases }: any) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  const pct = totalCases ? Math.round((p.count / totalCases) * 1000) / 10 : 0; // 1 decimal
  return (
    <div className="rounded-md border bg-white p-3 text-xs shadow">
      <div className="mb-1 font-medium">Transition</div>
      <div className="mb-1">{p.name}</div>
      <div>Typical worst-case (P90): {toHrsMins(p.p90)}</div>
      <div>Median: {toHrsMins(p.median)}</div>
      <div>Average: {toHrsMins(p.avg)}</div>
      <div className="mt-1">Count: {p.count} ({pct}% of cases)</div>
    </div>
  );
}

export default function MetricsDashboard() {
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const [topN, setTopN] = useState<number>(20);

  // --- process list ---
  const { data: processes } = useQuery({
    queryKey: ["monitoring", "processes"],
    queryFn: fetchProcesses,
  });

  // --- available date range ---
  const { data: range } = useQuery<ProcessRange>({
    queryKey: ["monitoring", "range", selectedProject],
    queryFn: () => fetchRange(selectedProject!),
    enabled: !!selectedProject,
  });

  // pick default
  useEffect(() => {
    if (!selectedProject && processes && processes.length > 0) {
      setSelectedProject(processes[0].project_id);
    }
  }, [processes, selectedProject]);

  // prefill range if empty
  useEffect(() => {
    if (range?.min && range?.max) {
      if (!start) setStart(range.min.slice(0, 16));
      if (!end) setEnd(range.max.slice(0, 16));
    }
  }, [range]); // eslint-disable-line

  // --- metrics data ---
  const { data: metrics, isFetching: loadingMetrics, refetch } = useQuery<MetricsPayload>({
    queryKey: ["monitoring", "metrics", selectedProject, start, end],
    queryFn: () => fetchMetrics(selectedProject!, toIsoUtc(start), toIsoUtc(end)),
    enabled: !!selectedProject,
  });

  const totalCases = metrics?.cases ?? 0;

  // chart data (include count for tooltips)
  const activityDataFull = useMemo(
    () =>
      (metrics?.activities || [])
        .map((a) => ({
          name: a.activity,
          p90: a.p90_seconds,
          avg: a.avg_seconds,
          median: a.median_seconds,
          count: a.count,
          is_bottleneck: a.is_bottleneck,
        }))
        .sort((a, b) => b.p90 - a.p90),
    [metrics]
  );

  const transitionDataFull = useMemo(
    () =>
      (metrics?.transitions || [])
        .map((t) => ({
          name: `${t.source_activity} → ${t.target_activity}`,
          p90: t.p90_seconds,
          avg: t.avg_seconds,
          median: t.median_seconds,
          count: t.count,
          is_bottleneck: t.is_bottleneck,
        }))
        .sort((a, b) => b.p90 - a.p90),
    [metrics]
  );

  const activityData = useMemo(() => activityDataFull.slice(0, topN), [activityDataFull, topN]);
  const transitionData = useMemo(() => transitionDataFull.slice(0, topN), [transitionDataFull, topN]);

  // Range for coloring (use displayed data)
  const actMin = useMemo(() => Math.min(...activityData.map((d) => d.p90)), [activityData]);
  const actMax = useMemo(() => Math.max(...activityData.map((d) => d.p90)), [activityData]);
  const transMin = useMemo(() => Math.min(...transitionData.map((d) => d.p90)), [transitionData]);
  const transMax = useMemo(() => Math.max(...transitionData.map((d) => d.p90)), [transitionData]);

  // --- UI (larger canvas, generous spacing, still with whitespace) ---
  return (
    <div className="mx-auto max-w-[1600px] xl:max-w-[1800px] px-6 lg:px-8 py-10 space-y-10">
      <h1 className="text-2xl font-semibold">Process Monitoring / Dashboards</h1>

      {!processes || processes.length === 0 ? (
        <p className="text-base text-muted-foreground">
          You do not have any mined processes yet. Start process mining or upload your own BPMN diagrams!
        </p>
      ) : (
        <>
          {/* Filters */}
          <div className="flex flex-wrap items-end gap-5">
            <div className="w-72">
              <label className="mb-1 block text-sm font-medium">Process</label>
              <Select
                value={selectedProject ? String(selectedProject) : undefined}
                onValueChange={(v) => setSelectedProject(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select process" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {processes.map((p: ProcessOption) => (
                    <SelectItem value={String(p.project_id)} key={p.project_id}>
                      {p.project_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="w-64">
              <label className="mb-1 block text-sm font-medium">Start date</label>
              <Input
                type="datetime-local"
                value={start}
                min={range?.min?.slice(0, 16)}
                max={range?.max?.slice(0, 16)}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="w-64">
              <label className="mb-1 block text-sm font-medium">End date</label>
              <Input
                type="datetime-local"
                value={end}
                min={range?.min?.slice(0, 16)}
                max={range?.max?.slice(0, 16)}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>

            <Button onClick={() => refetch()} disabled={!selectedProject || loadingMetrics} className="h-10 px-5">
              Apply Filters
            </Button>

            <div className="ml-auto flex items-end gap-2">
              <label className="text-sm text-muted-foreground">Top</label>
              <Select value={String(topN)} onValueChange={(v) => setTopN(Number(v))}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="9999">All</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Range info */}
          {range?.min && range?.max && (
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              Available data range:&nbsp;
              <span className="font-medium">
                {format(new Date(range.min), "yyyy-MM-dd HH:mm")} — {format(new Date(range.max), "yyyy-MM-dd HH:mm")}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setStart(range.min!.slice(0, 16));
                  setEnd(range.max!.slice(0, 16));
                }}
              >
                Use full range
              </Button>
            </div>
          )}

          {/* Summary */}
          <div className="text-base text-muted-foreground">
            {metrics ? (
              <>
                Showing <span className="font-medium">{metrics.cases}</span> cases
                {start && <> from <span className="font-medium">{format(new Date(start), "yyyy-MM-dd HH:mm")}</span></>}
                {end && <> to <span className="font-medium">{format(new Date(end), "yyyy-MM-dd HH:mm")}</span></>}
              </>
            ) : (
              <>No data yet.</>
            )}
          </div>

          {/* Charts */}
          {metrics && (activityData.length > 0 || transitionData.length > 0) ? (
            <div className="grid grid-cols-1 gap-10 2xl:gap-12 lg:grid-cols-2">
              <Card className="p-6 lg:p-7">
                <h3 className="mb-1 text-lg font-semibold">Activity Bottlenecks</h3>
                <p className="mb-5 text-sm text-muted-foreground">
                  Typical worst-case (P90) duration, by activity
                </p>
                <div className="h-[420px] md:h-[500px] xl:h-[560px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={activityData} margin={{ left: 12, right: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" hide />
                      <YAxis tickFormatter={(v) => toHrsMins(v)} />
                      <Tooltip content={(props) => <ActivityTooltip {...props} totalCases={totalCases} />} />
                      <Bar dataKey="p90">
                        {activityData.map((d, idx) => (
                          <Cell key={`act-${idx}`} fill={severityColor(d.p90, actMin, actMax, d.is_bottleneck)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card className="p-6 lg:p-7">
                <h3 className="mb-1 text-lg font-semibold">Transition Bottlenecks</h3>
                <p className="mb-5 text-sm text-muted-foreground">
                  Typical worst-case (P90) duration, by transition
                </p>
                <div className="h-[420px] md:h-[500px] xl:h-[560px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={transitionData} margin={{ left: 12, right: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" hide />
                      <YAxis tickFormatter={(v) => toHrsMins(v)} />
                      <Tooltip content={(props) => <TransitionTooltip {...props} totalCases={totalCases} />} />
                      <Bar dataKey="p90">
                        {transitionData.map((d, idx) => (
                          <Cell key={`tr-${idx}`} fill={severityColor(d.p90, transMin, transMax, d.is_bottleneck)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          ) : (
            <p className="text-base text-muted-foreground">No events found for the selected filters.</p>
          )}
        </>
      )}
    </div>
  );
}
