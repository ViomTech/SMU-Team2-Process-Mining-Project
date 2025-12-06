// Home.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getDashboardData } from "@/lib/api";
import { Link } from "react-router-dom";

import RecentBpmn from "@/components/bpmn/RecentBpmn";

// Shadcn UI & Icons
// import RecentRecommendationsPanel from "./RecentRecommendationsPanel";
// import type { Recommendation } from "../components/RecentRecommendations.types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Rocket, UploadCloud } from "lucide-react";

interface FileInfo {
  file_id: number;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: number; // 0: Uploaded, 1: Processed, 2: Failed
  upload_date: string;
}

interface DashboardData {
  files: FileInfo[];
  bpmnDiagramCount: number;
  lastDiscoveryRun: string | null;
}

const formatDate = (dateString: string) => {
  if (!dateString) return "N/A";
  return new Date(dateString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

// const fetchRecentRecommendations = async (): Promise<Recommendation[]> => {
//   return [
//     {
//       id: "1",
//       type: "Bottleneck",
//       description: "Approval step takes 2x average time",
//       timestamp: new Date().toISOString(),
//       link: "/process/approval",
//       ctaLabel: "View Process",
//     },
//     {
//       id: "2",
//       type: "Inefficiency",
//       description: "Manual entry detected in invoice processing",
//       timestamp: new Date(Date.now() - 3600000).toISOString(),
//       link: "/process/invoice",
//       ctaLabel: "Open Recommendation",
//     },
//     {
//       id: "3",
//       type: "Conformance deviation",
//       description: "Skipped validation step in 5 cases",
//       timestamp: new Date(Date.now() - 7200000).toISOString(),
//       link: "/process/validation",
//       ctaLabel: "View Process",
//     },
//   ];
// };

export default function Home() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, loading: authLoading } = useAuth();

  // --- Recommendations state (disabled for now) ---
  // const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  // const [recsLoading, setRecsLoading] = useState(true);

  // useEffect(() => {
  //   fetchRecentRecommendations()
  //     .then(setRecommendations)
  //     .finally(() => setRecsLoading(false));
  // }, []);

  // 🔒 Only fetch when auth is done AND user is ready
  useEffect(() => {
    if (!authLoading && user) {
      let cancelled = false;
      (async () => {
        try {
          const data = await getDashboardData();
          if (!cancelled) setDashboardData(data);;
        } catch (err: any) {
          if (!cancelled) setError(err?.message || "Failed to fetch dashboard data");
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
      return () => {
        cancelled = true;
      };
    } else if (!authLoading && !user) {
      // not authed
      setLoading(false);
    }
  }, [authLoading, user]);

  if (!dashboardData) {
    return <div className="p-8 text-center text-muted-foreground">Loading.</div>;
    }
    
  const { files, bpmnDiagramCount, lastDiscoveryRun } = dashboardData;
  // --- Data Ingestion ---
  const totalFiles = files.length;
  const sourceCount = new Set(files.map((f) => f.file_type)).size;
  const lastIngestionTime =
    files.length > 0
      ? formatDate(
          files.sort(
            (a, b) =>
              new Date(b.upload_date).getTime() -
              new Date(a.upload_date).getTime()
          )[0].upload_date
        )
      : "N/A";

  // --- Process Discovery ---
  const discoveredCount = bpmnDiagramCount;
  const pendingCount = files.filter((file) => file.status === 0).length;
  const discoveryStatus = pendingCount > 0 ? "In Progress" : "Success";

  // --- Optimization (mock) ---
  const optimizationData = { open: 3, applied: 27, status: "Action Required" };

  // include recsLoading to avoid empty-panel flash
  if (authLoading || loading /* || recsLoading */) {
    return <div className="p-8 text-center">Loading...</div>;
  }
  if (error) {
    return <div className="p-8 text-center text-red-500">Error: {error}</div>;
  }

  return (
    <main className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
      <div className="flex items-center">
        <h1 className="text-lg font-semibold md:text-2xl">Homepage</h1>
      </div>

      {/* Recent Recommendations (disabled for now) */}
      {/* <RecentRecommendationsPanel recommendations={recommendations.slice(0, 5)} /> */}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 md:gap-8 lg:grid-cols-3">
        {/* Data Ingestion Card */}
        <Link to="/projects">
          <Card className="h-full flex flex-col hover:border-primary transition-colors">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Data Ingestion
              </CardTitle>
              <UploadCloud className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="grow">
              {files.length === 0 ? (
                <p className="text-sm text-muted-foreground pt-2">
                  No data ingested yet.
                </p>
              ) : (
                <div className="grid gap-4">
                  <Badge className="w-fit">Success</Badge>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Total Files Uploaded
                      </p>
                      <p className="text-lg font-bold">{totalFiles}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Sources</p>
                      <p className="text-lg font-bold">{sourceCount}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Last Ingestion Time
                    </p>
                    <p className="text-sm">{lastIngestionTime}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </Link>

        {/* Process Discovery Card */}
        <Card className="h-full flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Process Discovery
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="flex-grow">
            {files.length === 0 ? (
              <p className="text-sm text-muted-foreground pt-2">
                Awaiting data ingestion.
              </p>
            ) : (
              <div className="grid gap-4">
                <Badge
                  variant={
                    discoveryStatus === "In Progress" ? "secondary" : "default"
                  }
                  className="w-fit"
                >
                  {discoveryStatus}
                </Badge>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Discovered</p>
                    <p className="text-lg font-bold">
                      {discoveredCount} Processes
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Pending</p>
                    <p className="text-lg font-bold">{pendingCount} File</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    Last Discovery Run
                  </p>
                  <p className="text-sm">{lastDiscoveryRun ? formatDate(lastDiscoveryRun) : "N/A"}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Optimization Card */}
        <Card className="h-full flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Optimization</CardTitle>
            <Rocket className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="flex-grow">
            <Badge
              variant={
                optimizationData.status === "Action Required"
                  ? "secondary"
                  : "default"
              }
            >
              {optimizationData.status}
            </Badge>
            <div className="mt-2 grid gap-2">
              <div>
                <p className="text-xs text-muted-foreground">
                  Open Recommendations
                </p>
                <p className="text-lg font-bold">{optimizationData.open}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">
                  Improvements Applied
                </p>
                <p className="text-sm">{optimizationData.applied}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Shortcuts to latest BPMN diagram */}
      <RecentBpmn />
    </main>
  );
}
