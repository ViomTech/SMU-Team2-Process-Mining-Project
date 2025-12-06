// Dashboard.tsx
"use client";

import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getDashboardData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import UploadButton from "@/components/Uploadbutton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { ArrowLeft } from "lucide-react";

interface FileInfo {
  file_id: number;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: number;
  upload_date: string;
}

export default function IngestionDashboard() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && user) {
      let cancelled = false;
      (async () => {
        try {
          const data = await getDashboardData();
          if (!cancelled) setFiles(data);
        } catch (err: any) {
          if (!cancelled) setError(err?.message || "Failed to fetch dashboard data");
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
      return () => { cancelled = true; };
    } else if (!authLoading && !user) {
      setLoading(false);
    }
  }, [authLoading, user]);

  const filteredFiles = useMemo(() => {
    if (statusFilter === "all") return files;
    const statusMap: Record<string, number> = { processed: 1, uploaded: 0 };
    return files.filter((file) => file.status === statusMap[statusFilter]);
  }, [files, statusFilter]);

  const statusMap = (status: number) => {
    switch (status) {
      case 0: return "Uploaded";
      case 1: return "Processed";
      case 2: return "Failed";
      default: return "Unknown";
    }
  };

  if (authLoading || loading) {
    return <div className="p-8 text-center">Loading Data...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-red-500">Error: {error}</div>;
  }

  return (
    <main className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
      <div className="flex items-center gap-4">
        <Link to="/">
          <Button variant="outline" size="icon" className="h-7 w-7">
            <ArrowLeft className="h-4 w-4" />
            <span className="sr-only">Back</span>
          </Button>
        </Link>
        <h1 className="flex-1 shrink-0 whitespace-nowrap text-xl font-semibold tracking-tight sm:grow-0">
          Data Ingestion
        </h1>
        <div className="ml-auto flex items-center gap-2">
          {/* <UploadButton
            userId={user?.user_id ?? 1}
            accept={{ "text/csv": [".csv"] }}
            onUploaded={async () => {
              try {
                const data = await getDashboardData();
                setFiles(data);
              } catch (e) {
                console.error(e);
              }
            }}
          /> */}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ingested Files</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={statusFilter} onValueChange={setStatusFilter}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="uploaded">Uploaded</TabsTrigger>
              <TabsTrigger value="processed">Processed</TabsTrigger>
            </TabsList>
            <TabsContent value={statusFilter} className="mt-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File ID</TableHead>
                      <TableHead>File Name</TableHead>
                      <TableHead>File Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Upload Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFiles.length > 0 ? (
                      filteredFiles.map((file) => (
                        <TableRow key={file.file_id}>
                          <TableCell>{file.file_id}</TableCell>
                          <TableCell className="font-medium">{file.filename}</TableCell>
                          <TableCell>{file.file_type}</TableCell>
                          <TableCell>{statusMap(file.status)}</TableCell>
                          <TableCell>{new Date(file.upload_date).toLocaleDateString()}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="h-24 text-center">
                          No files found.
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
    </main>
  );
}
