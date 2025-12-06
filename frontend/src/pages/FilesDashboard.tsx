// src/pages/FilesDashboard.tsx

import { useEffect, useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { getProjectById } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetClose,
} from "@/components/ui/sheet";import { ArrowLeft } from "lucide-react";
import UploadButton from "@/components/Uploadbutton";
import ProcessMiner from "@/components/ProcessMiner";
import ProjectBpmn from "@/components/bpmn/ProjectBpmn";
import ProjectRecommendation from "@/components/ProjectRecommendation";
import ProjectHistoryTable from "@/components/ProjectHistory";

interface FileInfo {
  file_id: number;
  filename: string;
  status: number; // 0 uploaded, 1 processed, 2 failed
  log_type?: string;
  upload_date: string;
}

interface ProjectDetail {
  project_id: number;
  project_name: string;
  description: string;
  created_at: string;
  files: FileInfo[];
}

export default function FilesDashboard() {
  const { projectId } = useParams<{ projectId: string }>();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isHistorySheetOpen, setIsHistorySheetOpen] = useState(false);

  const fetchProjectDetails = async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      const data = await getProjectById(projectId);
      setProject(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch project details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectDetails();
  }, [projectId]);

  const filteredFiles = useMemo(() => {
    if (!project?.files) return [];
    if (statusFilter === "all") return project.files;
    const statusMap: Record<string, number> = { processed: 1, uploaded: 0, failed: 2 };
    return project.files.filter((file) => file.status === statusMap[statusFilter]);
  }, [project, statusFilter]);

  const statusMap = (status: number) => {
    switch (status) {
      case 0: return "Uploaded";
      case 1: return "Processed";
      case 2: return "Failed";
      default: return "Unknown";
    }
  };

  if (loading) return <div className="p-8 text-center">Loading Project...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
  if (!project) return <div className="p-8 text-center">Project not found.</div>;

  return (
    <main className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
      {/* --- Header Section --- */}
      <div className="flex items-center gap-4">
        <Link to="/projects">
          <Button>
            <ArrowLeft className="h-4 w-4" />
            <span className="sr-only">Back</span>
          </Button>
        </Link>
        <h1 className="flex-1 shrink-0 whitespace-nowrap text-xl font-semibold tracking-tight sm:grow-0">
          {project.project_name}
        </h1>
        <div className="ml-auto flex items-center gap-2">
          {projectId && (
            <>
              <UploadButton
                projectId={projectId}
                onUploaded={fetchProjectDetails}
                // accept both structured CSV and unstructured logs
                accept={{
                  "text/csv": [".csv"],
                  "text/plain": [".log", ".txt"],
                }}
              />

              <ProcessMiner onDone={fetchProjectDetails} />

              <Sheet open={isHistorySheetOpen} onOpenChange={setIsHistorySheetOpen}>
                <SheetTrigger asChild>
                  <Button>View Approval History</Button>
                </SheetTrigger> 
                <SheetContent className="w-full sm:w-[600px] lg:w-[800px] overflow-y-auto">
                  <SheetHeader>
                    <SheetTitle>History</SheetTitle>
                  </SheetHeader> 
                  <div className="py-4 grow">
                    <ProjectHistoryTable projectId={projectId!} />
                  </div>
                  <div className="mt-auto flex justify-end">
                    <SheetClose asChild>
                      <Button>Close</Button>
                    </SheetClose>
                  </div>
                </SheetContent>
              </Sheet>
            </>
          )}
        </div>
      </div>

      <Card className="rounded-sm">
        <CardHeader>
          <CardTitle>Ingested Files</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={statusFilter} onValueChange={setStatusFilter}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="uploaded">Uploaded</TabsTrigger>
              <TabsTrigger value="processed">Processed</TabsTrigger>
              <TabsTrigger value="failed">Failed</TabsTrigger>
            </TabsList>
            <TabsContent value={statusFilter} className="mt-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File Index</TableHead>
                      <TableHead>File Name</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Upload Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFiles.length > 0 ? (
                      filteredFiles.map((file, index) => (
                        <TableRow key={file.file_id}>
                          <TableCell>{index + 1}</TableCell>
                          <TableCell className="font-medium">{file.filename}</TableCell>
                          <TableCell>{statusMap(file.status)}</TableCell>
                          <TableCell>{new Date(file.upload_date).toLocaleDateString()}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="h-24 text-center">
                          <p className="text-center text-gray-600 italic">No Files Ingested.</p>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>


      {/* IMPORTANT: provide projectId to ProjectBpmn so its View links include ?projectId=... */}
      {projectId && <ProjectBpmn projectId={projectId} />}

      <ProjectRecommendation />
    </main>
  );
}
