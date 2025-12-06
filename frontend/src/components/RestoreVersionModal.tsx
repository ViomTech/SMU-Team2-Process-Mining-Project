// src/components/RestoreVersionModal.tsx
import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { History, Copy } from "lucide-react";
import { toast } from "sonner";

interface Version {
  audit_id: number;
  version: number;
  saved_date: string;
  user_id: number;
  approval_status: boolean | null;
}

interface BpmnFile {
  bpmn_id: number;
  filename: string;
  version: number;
  upload_date: string;
  last_modified: string;
  description: string;
}

interface RestoreVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  bpmnId: number;
  projectId?: string;
  currentVersion: number;
  onRestored: () => void;
}

export default function RestoreVersionModal({
  isOpen,
  onClose,
  bpmnId,
  projectId,
  currentVersion,
  onRestored,
}: RestoreVersionModalProps) {
  // Version history state
  const [versions, setVersions] = useState<Version[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);

  // Other BPMN files state
  const [otherFiles, setOtherFiles] = useState<BpmnFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Selection state
  const [selectedVersion, setSelectedVersion] = useState<Version | null>(null);
  const [selectedFile, setSelectedFile] = useState<BpmnFile | null>(null);
  const [actionType, setActionType] = useState<"restore" | "clone" | null>(null);
  
  // UI state
  const [showConfirm, setShowConfirm] = useState(false);
  const [processing, setProcessing] = useState(false);

  // Fetch version history when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchVersionHistory();
      if (projectId) {
        fetchProjectFiles();
      }
    }
  }, [isOpen, bpmnId, projectId]);

  const fetchVersionHistory = async () => {
    try {
      setLoadingVersions(true);
      const res = await fetch(`/api/bpmn/get-version-history/${bpmnId}`, {
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error("Failed to fetch version history");
      }

      const data = await res.json();
      setVersions(data.versions || []);
    } catch (err: any) {
      toast.error(err.message || "Failed to load version history");
    } finally {
      setLoadingVersions(false);
    }
  };

  const fetchProjectFiles = async () => {
    if (!projectId) return;

    try {
      setLoadingFiles(true);
      const res = await fetch(`/api/bpmn/get-project-bpmn-files/${projectId}`, {
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error("Failed to fetch project BPMN files");
      }

      const data = await res.json();
      // Filter out current file
      const filtered = (data.bpmn_files || []).filter(
        (file: BpmnFile) => file.bpmn_id !== bpmnId
      );
      setOtherFiles(filtered);
    } catch (err: any) {
      toast.error(err.message || "Failed to load project files");
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleRestoreVersion = async () => {
    if (!selectedVersion) return;

    try {
      setProcessing(true);
      const res = await fetch("/api/bpmn/restore-version", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          bpmn_id: bpmnId,
          audit_id: selectedVersion.audit_id,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to restore version");
      }

      const result = await res.json();
      toast.success(
        `Version ${selectedVersion.version} restored as v${result.new_version}`
      );

      closeAndReset();
      onRestored();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleCloneFile = async () => {
    if (!selectedFile || !projectId) return;

    try {
      setProcessing(true);
      const res = await fetch("/api/bpmn/clone-bpmn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          source_bpmn_id: selectedFile.bpmn_id,
          project_id: parseInt(projectId),
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to clone file");
      }

      const result = await res.json();
      toast.success(
        `File '${selectedFile.filename}' (v${selectedFile.version}) cloned as v${result.new_version}`
      );

      closeAndReset();
      onRestored();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleVersionSelect = (version: Version) => {
    setSelectedVersion(version);
    setSelectedFile(null);
    setActionType("restore");
    setShowConfirm(true);
  };

  const handleFileSelect = (file: BpmnFile) => {
    setSelectedFile(file);
    setSelectedVersion(null);
    setActionType("clone");
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    console.log("🎯 handleConfirm called");
    console.log("🔧 actionType:", actionType);
    console.log("📁 selectedFile:", selectedFile);
    console.log("🔄 selectedVersion:", selectedVersion);
    
    if (actionType === "restore") {
      console.log("✅ Calling handleRestoreVersion");
      handleRestoreVersion();
    } else if (actionType === "clone") {
      console.log("✅ Calling handleCloneFile");
      handleCloneFile();
    } else {
      console.log("❌ No valid actionType, doing nothing");
    }
  };

  const closeAndReset = () => {
    setShowConfirm(false);
    setSelectedVersion(null);
    setSelectedFile(null);
    setActionType(null);
    onClose();
  };

  return (
    <>
      {/* Main Modal - Tabbed Interface */}
      <Dialog open={isOpen && !showConfirm} onOpenChange={closeAndReset}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Restore or Clone BPMN
            </DialogTitle>
            <DialogDescription>
              Restore a previous version of this file, or clone another file from this
              project.
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="versions" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="versions">Version History</TabsTrigger>
              <TabsTrigger value="files">Other Files</TabsTrigger>
            </TabsList>

            {/* Tab 1: Version History */}
            <TabsContent value="versions" className="mt-4">
              {loadingVersions ? (
                <div className="py-8 text-center text-muted-foreground">
                  Loading version history...
                </div>
              ) : versions.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  No previous versions found. Make edits and save to create version
                  history.
                </div>
              ) : (
                <div className="max-h-96 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Version</TableHead>
                        <TableHead>Saved Date</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {versions.map((version) => (
                        <TableRow key={version.audit_id}>
                          <TableCell className="font-medium">
                            v{version.version.toFixed(1)}
                          </TableCell>
                          <TableCell>
                            {new Date(version.saved_date).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            {version.approval_status === true && (
                              <span className="text-emerald-600">Approved</span>
                            )}
                            {version.approval_status === false && (
                              <span className="text-red-600">Rejected</span>
                            )}
                            {version.approval_status === null && (
                              <span className="text-gray-500">-</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleVersionSelect(version)}
                            >
                              <History className="h-3 w-3 mr-1" />
                              Restore
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            {/* Tab 2: Other Files */}
            <TabsContent value="files" className="mt-4">
              {!projectId ? (
                <div className="py-8 text-center text-muted-foreground">
                  Project ID not available.
                </div>
              ) : loadingFiles ? (
                <div className="py-8 text-center text-muted-foreground">
                  Loading project files...
                </div>
              ) : otherFiles.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  No other BPMN files in this project.
                </div>
              ) : (
                <div className="max-h-96 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Filename</TableHead>
                        <TableHead>Version</TableHead>
                        <TableHead>Last Modified</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {otherFiles.map((file) => (
                        <TableRow key={file.bpmn_id}>
                          <TableCell className="font-medium">
                            {file.filename}
                          </TableCell>
                          <TableCell>v{file.version.toFixed(1)}</TableCell>
                          <TableCell>
                            {new Date(file.last_modified).toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleFileSelect(file)}
                            >
                              <Copy className="h-3 w-3 mr-1" />
                              Clone
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button variant="outline" onClick={closeAndReset}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation Modal */}
      <Dialog open={showConfirm} onOpenChange={() => setShowConfirm(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === "restore" ? "Confirm Version Restoration" : "Confirm File Clone"}
            </DialogTitle>
            <DialogDescription>
              {actionType === "restore" && selectedVersion ? (
                <>
                  Are you sure you want to restore version{" "}
                  <strong>v{selectedVersion.version.toFixed(1)}</strong>?
                </>
              ) : actionType === "clone" && selectedFile ? (
                <>
                  Are you sure you want to clone{" "}
                  <strong>
                    {selectedFile.filename} (v{selectedFile.version.toFixed(1)})
                  </strong>
                  ?
                </>
              ) : null}
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-800">
              {actionType === "restore" && selectedVersion ? (
                <>
                  ℹ️ This will create a new version (v
                  {(currentVersion + 0.1).toFixed(1)}) as a copy of version{" "}
                  {selectedVersion.version.toFixed(1)}. Your current work will be saved
                  in the version history.
                </>
              ) : actionType === "clone" && selectedFile ? (
                <>
                  ℹ️ This will create a new BPMN file with the content from{" "}
                  {selectedFile.filename} (v{selectedFile.version.toFixed(1)}). The new
                  file will appear in your project with a new version number.
                </>
              ) : null}
            </p>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConfirm(false)}
              disabled={processing}
            >
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={processing}>
              {processing
                ? "Processing..."
                : actionType === "restore"
                ? "Confirm Restore"
                : "Confirm Clone"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
