import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import BpmnDropzone from "@/components/bpmn/BpmnDropzone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

interface UploadBpmnProps {
  triggerElement?: React.ReactNode 
}

export default function UploadBpmn({ triggerElement }: UploadBpmnProps) {
  const [bpmnFile, setBpmnFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const [openDialog, setOpenDialog] = useState<boolean>(false);

  const navigate = useNavigate();

  useEffect(() => {
    if (bpmnFile && title === "") {
      const nameWithoutExtension = bpmnFile.name.replace(/\.[^/.]+$/, "");
      setTitle(nameWithoutExtension);
    }
  }, [bpmnFile]);

  const handleUpload = async () => {
    if (!bpmnFile) {
      toast.error("Please select a BPMN file.");
      return;
    }

    try {
      setUploading(true);

      const xmlContent = await bpmnFile.text();
      const filenameToUse = title || bpmnFile.name.replace(/\.[^/.]+$/, "");

      const res = await fetch("/api/bpmn/save-bpmn", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          filename: filenameToUse,
          bpmn_xml: xmlContent,
          description
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Upload failed.");
      }

      toast.success("BPMN uploaded successfully.");

      setBpmnFile(null);
      setTitle("");
      setDescription("");
      setOpenDialog(false);

      navigate(`/bpmn/view/${data.id}`);

    } catch (error: any) {
      console.error(error.message);
      toast.error("Failed to upload BPMN. Please try again.");

    } finally {
      setUploading(false);
    }
  }

  return (
    <Dialog open={openDialog} onOpenChange={setOpenDialog}>
      <DialogTrigger asChild>
        { triggerElement || (
          <Button>Upload BPMN</Button>
        )}
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload BPMN</DialogTitle>
          <DialogDescription>Select a BPMN/XML file to upload. Duplicate files are not allowed.</DialogDescription>
        </DialogHeader>

        <Input placeholder="Enter BPMN title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Textarea placeholder="Optional description..." value={description} onChange={(e) => setDescription(e.target.value)} />
        
        <BpmnDropzone onFileSelected={setBpmnFile} />

        <DialogFooter>
          <DialogClose asChild>
            <Button>Cancel</Button>
          </DialogClose>

          <Button onClick={handleUpload} disabled={uploading || !bpmnFile}>{uploading ? "Uploading" : "Upload BPMN"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}