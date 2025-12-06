import { useState } from "react";
import { useNavigate } from "react-router-dom";
import BpmnDiagram from "@/components/bpmn/BpmnDiagram";
import {
  Card,
  CardHeader,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { EllipsisVertical, ChevronDown } from "lucide-react";

type Props = {
  id: number;
  name: string;
  upload_date: string;
  onDelete?: (id: number) => void;
  /** Optional: when missing we’ll resolve it before navigating. */
  projectId?: string;
};

export default function BpmnCard({ id, name, upload_date, onDelete, projectId }: Props) {
  const [bpmnName, setBpmnName] = useState<string>(name);
  const [bpmnDescription, setBpmnDescription] = useState<string>("");
  const [openEditInfo, setOpenEditInfo] = useState<boolean>(false);
  const [openDelete, setOpenDelete] = useState<boolean>(false);
  const [resolving, setResolving] = useState<boolean>(false);

  const navigate = useNavigate();
  const formattedDate = new Date(upload_date).toLocaleDateString("en-SG", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "Asia/Singapore",
  });
  const formattedTime = new Date(upload_date).toLocaleTimeString("en-SG", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Singapore",
  });

  // Small helper to ensure requests go through your fetch shim + include cookies
  const apiGet = async (path: string) => {
    const res = await fetch(path, { credentials: "include" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res;
  };

  // --- NEW: programmatic BPMN download (fixes 404 on GitHub Pages) ---
  const handleBpmnDownload = async () => {
    try {
      const res = await apiGet(`/api/bpmn/download/${id}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${bpmnName || "diagram"}.bpmn`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("BPMN downloaded successfully!");
    } catch (err) {
      console.error("BPMN download error:", err);
      toast.error("Failed to download BPMN");
    }
  };

  // --- ALWAYS ensure we have a projectId before navigating to view ---
  const handleView = async () => {
    if (projectId) {
      navigate(`/bpmn/view/${id}?projectId=${projectId}`);
      return;
    }
    try {
      setResolving(true);
      const res = await fetch(`/api/bpmn/get-info/${id}`, { credentials: "include" });
      if (!res.ok) throw new Error(`Failed to resolve project for BPMN ${id}`);
      const info = await res.json();
      const pid = String(info.project_id ?? "").trim();
      if (pid) {
        navigate(`/bpmn/view/${id}?projectId=${pid}`);
      } else {
        navigate(`/bpmn/view/${id}`);
      }
    } catch (err) {
      console.error(err);
      navigate(`/bpmn/view/${id}`);
    } finally {
      setResolving(false);
    }
  };

  const handleSvgExport = async () => {
    try {
      const res = await fetch(`/api/bpmn/export-svg/${id}`);
      if (!res.ok) throw new Error("Failed to fetch BPMN data");
      const data = await res.json();

      const BpmnViewer = (await import("bpmn-js/lib/NavigatedViewer")).default;
      const tempContainer = document.createElement("div");
      tempContainer.style.position = "absolute";
      tempContainer.style.left = "-9999px";
      tempContainer.style.width = "800px";
      tempContainer.style.height = "600px";
      document.body.appendChild(tempContainer);

      const viewer = new BpmnViewer({ container: tempContainer, width: 800, height: 600 });
      await viewer.importXML(data.xml);

      const { svg } = await viewer.saveSVG();

      viewer.destroy();
      document.body.removeChild(tempContainer);

      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${data.filename}.svg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success("SVG downloaded successfully!");
    } catch (error) {
      console.error("SVG export error:", error);
      toast.error("Failed to export SVG");
    }
  };

  const handlePngExport = async () => {
    try {
      const res = await fetch(`/api/bpmn/export-svg/${id}`);
      if (!res.ok) throw new Error("Failed to fetch BPMN data");
      const data = await res.json();

      const BpmnViewer = (await import("bpmn-js/lib/NavigatedViewer")).default;
      const tempContainer = document.createElement("div");
      tempContainer.style.position = "absolute";
      tempContainer.style.left = "-9999px";
      tempContainer.style.width = "800px";
      tempContainer.style.height = "600px";
      document.body.appendChild(tempContainer);

      const viewer = new BpmnViewer({ container: tempContainer, width: 800, height: 600 });
      await viewer.importXML(data.xml);

      const { svg } = await viewer.saveSVG();

      viewer.destroy();
      document.body.removeChild(tempContainer);

      const img = new Image();
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get canvas context");

      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${data.filename}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            toast.success("PNG downloaded successfully!");
          }
        }, "image/png");
      };
      img.onerror = () => {
        throw new Error("Failed to load SVG image");
      };
      const svgBlob = new Blob([svg], { type: "image/svg+xml" });
      const svgUrl = URL.createObjectURL(svgBlob);
      img.src = svgUrl;
    } catch (error) {
      console.error("PNG export error:", error);
      toast.error("Failed to export PNG");
    }
  };

  const handleUpdateInfo = async () => {
    try {
      const res = await fetch(`/api/bpmn/update-bpmn-info/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: bpmnName,
          description: bpmnDescription,
        }),
      });

      if (!res.ok) throw new Error("Failed to update BPMN info");

      toast.success("BPMN title/description updated!");
      setOpenEditInfo(false);
    } catch (error) {
      toast.error("Could not update BPMN info.");
    }
  };

  const handleDeleteBpmn = async () => {
    try {
      const res = await fetch(`/api/bpmn/delete-bpmn/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete BPMN.");
      toast.success("BPMN deleted successfully");
      if (onDelete) onDelete(id);
      setOpenDelete(false);
    } catch (error: any) {
      toast.error(error.message || "Failed to delete BPMN.");
    }
  };

  return (
    <div className="bpmn-card w-full max-w-xs">
      <Card className="h-auto flex flex-col justify-between w-full max-w-sm">
        <CardHeader className="flex flex-row justify-between">
          <div>
            <CardTitle className="line-clamp-1">{bpmnName}</CardTitle>
            <CardDescription className="italic text-xs">
              {formattedDate} {formattedTime}
            </CardDescription>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <EllipsisVertical />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setOpenEditInfo(true)}>
                Edit name or description
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setOpenDelete(true)}>Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardHeader>

        <CardContent className="flex flex-col flex-1">
          <div className="h-[120px] overflow-hidden">
            <BpmnDiagram id={id} height="120px" />
          </div>

          <CardAction className="flex flex-row gap-2 mt-4 justify-end">
            {/* View button now guarantees projectId before navigating */}
            <Button onClick={handleView} disabled={resolving}>
              {resolving ? "Opening…" : "View"}
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button>
                  Download <ChevronDown className="ml-1 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="bottom">
                <DropdownMenuItem onClick={handleSvgExport}>Download as SVG</DropdownMenuItem>
                <DropdownMenuItem onClick={handlePngExport}>Download as PNG</DropdownMenuItem>

                {/* REPLACED <a href="/api/bpmn/download/:id">…</a> with programmatic fetch */}
                <DropdownMenuItem onClick={handleBpmnDownload}>
                  Download as BPMN
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </CardAction>
        </CardContent>
      </Card>

      <Dialog open={openEditInfo} onOpenChange={setOpenEditInfo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit BPMN Information</DialogTitle>
            <DialogDescription>
              Update the name and description for this BPMN diagram.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={bpmnName}
                onChange={(e) => setBpmnName(e.target.value)}
                placeholder="Enter new name"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={bpmnDescription}
                onChange={(e) => setBpmnDescription(e.target.value)}
                placeholder="Enter new description"
              />
            </div>
          </div>

          <DialogFooter>
            <Button onClick={handleUpdateInfo}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={openDelete} onOpenChange={setOpenDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete BPMN</DialogTitle>
            <p>
              Are you sure you want to delete this BPMN? Note that this action{" "}
              <span className="font-semibold">cannot</span> be reversed.
            </p>
          </DialogHeader>

          <DialogFooter>
            <Button onClick={() => setOpenDelete(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteBpmn}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
