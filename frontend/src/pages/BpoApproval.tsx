// src/pages/BpoApproval.tsx
import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import ApprovalModal from "@/components/ApprovalModal";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";

interface Approval {
  approval_id: number;
  bpmnfile_id: number;
  processname: string;
  filename: string;
  version: number;
  submitted_by: number;
  submitted_by_name: string;
  status: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export default function ApprovalsPage() {
  const [allApprovals, setAllApprovals] = useState<Approval[]>([]);
  const [activeTab, setActiveTab] = useState("pending"); // default tab
  const [loading, setLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<Approval | null>(null);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);

  const navigate = useNavigate();

  // --- Fetch approvals ---
  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/bpmn/get-bpo-approvals", { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch approvals.");
      const data = await res.json();
      setAllApprovals(data.bpmn_files);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  // --- Filter approvals per tab ---
  const filteredApprovals = useMemo(() => {
    if (activeTab === "all") return allApprovals;

    return allApprovals.filter((req) => {
        return req.status === activeTab;
    });
    }, [allApprovals, activeTab]);

  // --- Modal helpers ---
  const openDecisionModal = (request: Approval, decisionType: "approved" | "rejected") => {
    setSelectedRequest(request);
    setDecision(decisionType);
    setIsModalOpen(true);
  };

  // Confirm decision
  const handleConfirmDecision = async (comment: string) => {
    if (!selectedRequest || !decision) {
      toast.error("No request selected.");
      return;
    }

    try {
      const res = await fetch("/api/bpmn/review-approval", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approval_id: selectedRequest.approval_id,
          approved: decision === "approved",
          comment,
        }),
        credentials: "include",
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `Failed to ${decision} request.`);
      }

      toast.success(`Request has been ${decision}.`);
      fetchApprovals();
      setIsModalOpen(false);
      setSelectedRequest(null); // clear only after success
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  if (loading) return <div className="p-8 text-center">Loading approvals...</div>;

  return (
    <div className="page mt-4 px-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Process Approvals</h1>
        <p className="text-gray-600 mt-1">Review pending requests and view past decisions.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Approval Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="pending">Pending</TabsTrigger>
              <TabsTrigger value="approved">Approved</TabsTrigger>
              <TabsTrigger value="rejected">Rejected</TabsTrigger>
              <TabsTrigger value="all">All</TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="mt-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Process Name</TableHead>
                      <TableHead>Version</TableHead>
                      <TableHead>Submitted By</TableHead>
                      <TableHead>Submitted At</TableHead>
                      <TableHead>Reviewed At</TableHead>
                      <TableHead>Status</TableHead>
                      {activeTab === "pending" && <TableHead className="text-right">Actions</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredApprovals.length > 0 ? (
                      filteredApprovals.map((req) => (
                        <TableRow key={req.approval_id}>
                          <TableCell className="font-medium">{req.processname}</TableCell>
                          <TableCell>{req.version.toFixed(1)}</TableCell>
                          <TableCell>{req.submitted_by_name}</TableCell>
                          <TableCell>{new Date(req.created_at).toLocaleString()}</TableCell>
                          <TableCell>{req.reviewed_at ? new Date(req.reviewed_at).toLocaleString() : "-"}</TableCell>
                          <TableCell>{req.status ?? "pending"}</TableCell>
                          <TableCell className="text-right space-x-2">
                            {activeTab === "pending" && (
                              <Button variant="outline" size="sm" onClick={() => navigate(`/bpmn/view/${req.bpmnfile_id}`)}>
                                View Details
                              </Button>
                            )}
                            {req.status === "pending" && (
                              <>
                                <Button size="sm" className="bg-red-500 hover:bg-red-700" onClick={() => openDecisionModal(req, "rejected")}>
                                  Reject
                                </Button>
                                <Button size="sm" className="bg-emerald-500 hover:bg-emerald-700" onClick={() => openDecisionModal(req, "approved")}>
                                  Approve
                                </Button>
                              </>
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                    <TableRow>
                      <TableCell colSpan={activeTab === "pending" ? 7 : 6} className="h-24 text-center">
                        {activeTab === "pending" && "No pending approvals found."}
                        {activeTab === "approved" && "No approved approvals found."}
                        {activeTab === "rejected" && "No rejected approvals found."}
                        {activeTab === "all" && "No approvals found."}
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

      {/* --- Decision Modal --- */}
      <ApprovalModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        selectedRequest={selectedRequest}
        decision={decision}
        onConfirm={handleConfirmDecision}
      />
    </div>
  );
}
