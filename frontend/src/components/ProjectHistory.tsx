// src/components/ProcessHistoryTable.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { toast } from "sonner";

interface HistoryEntry {
  approval_id: number;
  bpmn_filename: string;
  from_state: string;
  to_state: string;
  status: string;
  comment: string | null;
  version: number | null;
  submitted_by: number;
  reviewed_by: number | null;
  created_at: string;
  reviewed_at: string | null;
}

interface Props {
  projectId: number | string;
}

export default function ProjectHistoryTable({ projectId }: Props) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    const fetchHistory = async () => {
      try {
        const res = await fetch(`/api/bpmn/${projectId}/history`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to fetch history");
        const data = await res.json();
        setHistory(data.history);
      } catch (err: any) {
        toast.error(err.message || "Error fetching history");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [projectId]);

  if (loading) return <div className="p-4 text-center">Loading history...</div>;

  return (
    <Card className="rounded-sm mt-6">
      <CardHeader>
        <CardTitle>Approval History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>BPMN</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>From State</TableHead>
                <TableHead>To State</TableHead>
                <TableHead>Comment</TableHead>
                <TableHead>Submitted By</TableHead>
                <TableHead>Reviewed By</TableHead>
                <TableHead>Reviewed At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.length > 0 ? (
                history.map((entry) => (
                  <TableRow key={entry.approval_id}>
                    <TableCell className="font-medium">{entry.bpmn_filename}</TableCell>
                    <TableCell>{entry.version != null ? entry.version.toFixed(1) : "-"}</TableCell>
                    <TableCell>{entry.from_state}</TableCell>
                    <TableCell>{entry.to_state}</TableCell>
                    <TableCell>{entry.comment ?? "-"}</TableCell>
                    <TableCell>{entry.submitted_by}</TableCell>
                    <TableCell>{entry.reviewed_by ?? "-"}</TableCell>
                    <TableCell>{entry.reviewed_at ? new Date(entry.reviewed_at).toLocaleString() : "-"}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center">
                    No approvals found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
