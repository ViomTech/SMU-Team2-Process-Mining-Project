"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { toast } from "sonner";

const API_URL = import.meta.env.VITE_API_URL as string;

type Props = {
  projectId: string | number;
  accept?: Record<string, string[]>;
  onUploaded?: () => void;
};

export default function UploadButton({
  projectId,
  accept = { "text/csv": [".csv"], "text/plain": [".txt", ".log"], "application/json": [".json"] },
  onUploaded,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const acceptAttr = Object.values(accept).flat().join(",");

  const openPicker = () => inputRef.current?.click();

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // --- THIS IS THE CHANGE ---
    // Merge new files with existing files
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setSelectedFiles(prevFiles => [...prevFiles, ...newFiles]);
    }
  };

  const upload = async () => {
    if (selectedFiles.length === 0) return;
    setBusy(true);
    
    const uploadPromises = selectedFiles.map(file => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("project_id", String(projectId));

      return fetch(`${API_URL}/api/file/upload-file`, {
        method: "POST",
        credentials: "include",
        body: formData,
      }).then(res => {
        if (!res.ok) {
          return res.json().then(err => Promise.reject({ fileName: file.name, message: err.message }));
        }
        return { fileName: file.name, status: 'success' };
      });
    });

    try {
      await Promise.all(uploadPromises);
      toast.success(`${selectedFiles.length} file(s) uploaded successfully!`);

      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.();

    } catch (error: any) {
      toast.error(`Upload failed for ${error.fileName}: ${error.message || "Unknown error"}`);
    } finally {
      setBusy(false);
    }
  };
  
  const getSelectedFilesText = () => {
    if (selectedFiles.length === 0) return "Choose file(s)";
    if (selectedFiles.length === 1) return selectedFiles[0].name;
    return `${selectedFiles.length} files selected`;
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={acceptAttr}
        className="hidden"
        onChange={onChange}
        multiple
      />

      <Button variant="outline" onClick={openPicker} disabled={busy}>
        <Upload className="mr-2 h-4 w-4" />
        {getSelectedFilesText()}
      </Button>

      {/* Add a button to clear the selection */}
      {selectedFiles.length > 0 && (
        <Button onClick={() => setSelectedFiles([])}>Clear</Button>
      )}

      <Button onClick={upload} disabled={selectedFiles.length === 0 || busy}>
        {busy ? "Uploading…" : "Upload"}
      </Button>
    </div>
  );
}