import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useState, useEffect } from "react";

interface Approval {
  approval_id: number;
  filename: string;
}

interface DecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedRequest: Approval | null;
  decision: "approved" | "rejected" | null;
  onConfirm: (comment: string) => Promise<void>;
}

export default function ApprovalModal({
  isOpen,
  onClose,
  selectedRequest,
  decision,
  onConfirm,
}: DecisionModalProps) {
  const [comment, setComment] = useState("");

  // Reset comment whenever modal opens or selectedRequest changes
  useEffect(() => {
    if (isOpen) setComment("");
  }, [isOpen, selectedRequest]);

  const handleConfirm = async () => {
    if (!comment.trim()) {
      toast.error("Please provide a reason for your decision.");
      return;
    }

    await onConfirm(comment); // send comment to parent
    // Do NOT clear selectedRequest here — parent will handle it
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Confirm Decision: {decision === "approved" ? "Approve" : "Reject"}
          </DialogTitle>
          <DialogDescription>
            Please provide a reason for your decision{selectedRequest ? ` on "${selectedRequest.filename}"` : ""}.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Textarea
            placeholder="Add your comments here..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={4}
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            className={decision === "approved" ? "bg-emerald-500 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700"}
          >
            Confirm {decision === "approved" ? "Approval" : "Rejection"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}