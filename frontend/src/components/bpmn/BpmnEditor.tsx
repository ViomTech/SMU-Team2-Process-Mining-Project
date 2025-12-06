// src/components/bpmn/BpmnEditor.tsx
import { useState, useRef, useEffect, useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import ApprovalModal from "@/components/ApprovalModal";
import BpmnModeler from "bpmn-js/lib/Modeler";
import EmbeddedCommentsModule from "bpmn-js-embedded-comments";
import { useBpmnXml } from "@/hooks/useBpmnXml";
// @ts-ignore
import { layoutProcess } from "bpmn-auto-layout";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn-embedded.css";
import "bpmn-js-embedded-comments/assets/comments.css";
import "@/assets/comments.css";
import { submitForApproval } from "@/lib/api";
import RestoreVersionModal from "@/components/RestoreVersionModal";
import { History } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, ChevronRight, Check, X, Send } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

import {
  makeRecommendationPath,
  type BottleneckMetric,
} from "@/lib/bottlenecks";

import { formatDurationSec } from "@/lib/time";

type BpmnEditorProps = {
  id: number;
  projectId?: string;
  highlights?: BottleneckMetric[]; // used for side panel & red dots
  userRole?: string;
};

interface EmbeddedComments {
  create: (elementId: string, comment: any) => void;
  update: (elementId: string, commentId: string, updates: any) => void;
  remove: (elementId: string, commentId: string) => void;
  collapseAll: () => void;
}
interface EventBus {
  on: (event: string, cb: (e: any) => void) => void;
  off: (event: string, cb: (e: any) => void) => void;
}

interface BpoInfo {
  id: number,
  email: string
}

interface Approval {
  approval_id: number;
  bpmnfile_id: number;
  processname: string;
  filename: string;
  version: number;
  submitted_by: number;
  status: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export default function BpmnEditor({ id, projectId, highlights = [], userRole }: BpmnEditorProps) {
  const { bpmnXml, loading, error } = useBpmnXml(id);
  const { user } = useAuth();
  const [bpmnName, setBpmnName] = useState<string>("");
  const [bpmnDescription, setBpmnDescription] = useState<string>("");
  const [bpmnVersion, setBpmnVersion] = useState<string>("");
  const [openSheet, setOpenSheet] = useState(false);
  const [localComments, setLocalComments] = useState<Record<string, any[]>>({});
  const [bpo, setBpo] = useState<BpoInfo>();
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);

  // ---- Bottlenecks: internal source-of-truth when props are empty ----
  const [bnLoading, setBnLoading] = useState(false);
  const [bnFetched, setBnFetched] = useState<BottleneckMetric[] | null>(null);
  const effectiveHighlights: BottleneckMetric[] = (highlights?.length ? highlights : (bnFetched || []));

  // Track model import completion (true after import + initial render)
  const [modelImported, setModelImported] = useState(false);

  // Modal for approval
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<Approval | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<"approved" | "rejected" | null>(null);
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<BpmnModeler | null>(null);
  const commentsRef = useRef<EmbeddedComments | null>(null);

  // Track overlay ids per element for bottleneck markers
  const overlayIdsRef = useRef<Map<string, string>>(new Map());

  const didForceBnRefreshRef = useRef(false);
  const repaintHandlerAttachedRef = useRef(false);

  const BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL";

  // --- meta fetchers ---
  const getBpo = async () => {
    try {
      const res = await fetch(`/api/bpmn/get-bpmn-bpo/${id}`);
      if (!res.ok) throw new Error("Failed to fetch BPO info");
      const data = await res.json();
      setBpo(data);
    } catch (err) {
      console.error("Error fetching BPO info:", err);
      setBpo(undefined);
    }
  };

  const getBpmnInfo = async () => {
    try {
      const res = await fetch(`/api/bpmn/get-info/${id}`);
      console.log(res);
      if (!res.ok) throw new Error(`Failed to fetch BPMN info: ${res.status}`);
      const info = await res.json();
      setBpmnName(info.filename);
      setBpmnDescription(info.description);
      setBpmnVersion(info.version.toFixed(1).toString());
    } catch (err) {
      console.error("Failed to fetch BPMN info", err);
    }
  };

  const getApproval = async () => {
    const res = await fetch(`/api/bpmn/get-bpmn-approval/${id}`);
    if (!res.ok) { 
      console.error("Failed to fetch BPMN approval."); 
      return; 
    }
    const data = await res.json();
    setSelectedRequest(data);
  }

  const getApprovalStatus = async () => {
    const res = await fetch(`/api/bpmn/get-approval-status/${id}`);
    if (!res.ok) { 
      console.error("Failed to fetch BPMN approval status."); 
      setApprovalStatus("Not Submitted");
      return; 
    }
    const data = await res.json();
    const status = data.approval_status;
    setApprovalStatus(status);
  };

  useEffect(() => {
    if (user) {
      getBpmnInfo();

      if (projectId) {
        getBpo();
        getApproval();
        getApprovalStatus();
      }
    }
  }, [user]);

  useEffect(() => {
    if (!user || !bpo) return;
    getApproval();
    getApprovalStatus();
  }, [user, bpo]);


  // ===== FOOLPROOF: force one bottleneck refresh on first mount if none were passed =====
  const fetchBottlenecks = async (forceRefresh = false) => {
    if (!projectId) return;
    try {
      setBnLoading(true);
      const url = `/api/process-mining/bottlenecks/${projectId}${forceRefresh ? "?refresh=1" : ""}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to fetch bottlenecks (${res.status})`);
      const data = await res.json();
      setBnFetched(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      setBnFetched([]);
    } finally {
      setBnLoading(false);
    }
  };

  useEffect(() => {
    if (!projectId) return;
    if (highlights?.length) return; // props already provided
    if (didForceBnRefreshRef.current) return;
    didForceBnRefreshRef.current = true;
    fetchBottlenecks(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const openDecisionModal = (decisionType: "approved" | "rejected") => {
    setSelectedDecision(decisionType);
    setIsModalOpen(true);
  };

  const handleConfirmDecision = async (comment: string) => {
    if (!selectedRequest || !selectedDecision) {
      toast.error("No request selected.");
      return;
    }
    try {
      const res = await fetch("/api/bpmn/review-approval", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approval_id: selectedRequest.approval_id,
          approved: selectedDecision === "approved",
          comment,
        }),
        credentials: "include",
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `Failed to ${selectedDecision} request.`);
      }
      toast.success(`Request has been ${selectedDecision}.`);
      setIsModalOpen(false);
      setSelectedDecision(null);
      getApprovalStatus(); // refresh status
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleVersionRestored = () => {
    window.location.reload();
  };

  // --- Embedded comments ---
  const setupEmbeddedComments = (xmlToImport: string) => {
    if (!modelerRef.current) return;
    const comments = modelerRef.current.get("comments") as EmbeddedComments | undefined;
    if (!comments) {
      console.error("Embedded comments service not found");
      toast.error("Comments feature unavailable");
      return;
    }
    commentsRef.current = comments;
    comments.collapseAll?.();

    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlToImport, "application/xml");
    const elements = xmlDoc.getElementsByTagName("*");
    const initialComments: Record<string, any[]> = {};

    Array.from(elements).forEach((el) => {
      const extComments =
        el.querySelector("bpmn\\:extensionElements > comments") ||
        el.querySelector("extensionElements > comments");
      if (!extComments) return;
      const elId = el.getAttribute("id");
      if (!elId) return;

      try {
        const parsed = JSON.parse(extComments.textContent || "[]");
        if (Array.isArray(parsed) && parsed.length > 0) {
          initialComments[elId] = parsed;
          parsed.forEach((comment) => {
            comments.create(elId)({
              id: comment.id || `c_${Date.now()}_${Math.random()}`,
              text: comment.text || comment.content || "",
              author: comment.author || "Unknown",
              date: comment.date || comment.timestamp || new Date().toISOString(),
            } as any);
          });
        }
      } catch (err) {
        console.warn(`Failed to parse comments for ${elId}`, err);
      }
    });

    setLocalComments(initialComments);
    setupCommentEventHandlers();
  };

  const setupCommentEventHandlers = () => {
    if (!modelerRef.current || !commentsRef.current) return;
    const eventBus = modelerRef.current.get("eventBus") as EventBus | undefined;
    if (!eventBus) return;

    ["comment.create", "comment.update", "comment.delete"].forEach((evt) => {
      eventBus.on(evt, (e: any) => {
        const elId = e.element?.id;
        if (!elId) return;
        setLocalComments((prev) => {
          const updated = { ...prev };
          updated[elId] = e.comments || [];
          return updated;
        });
      });
    });
  };

  const handleSubmitForApproval = async () => {
    if (!id) {
      toast.error("BPMN ID is missing.");
      return;
    }
    if (!bpo?.id) {
      toast.error("BPO not loaded yet. Please wait.");
      return;
    }
    try {
      const result = await submitForApproval(id, bpo.id);
      toast.success(result.message || "Submitted successfully!");
    } catch (err: any) {
      toast.error(err.message || "Failed to submit for approval.");
      console.error(err);
    }
  };

  const handleSaveBpmn = async () => {
    if (!modelerRef.current) return;
    try {
      const { xml: rawXml } = (await modelerRef.current.saveXML({ format: true })) as any;
      const parser = new DOMParser();
      const serializer = new XMLSerializer();
      const xmlDoc = parser.parseFromString(rawXml, "application/xml");

      Object.entries(localComments).forEach(([elId, comments]) => {
        const el = xmlDoc.querySelector(`[id="${elId}"]`);
        if (!el) return;

        let extEl =
          el.querySelector("bpmn\\:extensionElements") ||
          el.querySelector("extensionElements");
        if (!extEl) {
          extEl = xmlDoc.createElementNS(BPMN_NS, "bpmn:extensionElements");
          el.appendChild(extEl);
        }

        let commentsEl = extEl.querySelector("comments");
        if (!commentsEl) {
          commentsEl = xmlDoc.createElementNS(BPMN_NS, "comments");
          extEl.appendChild(commentsEl);
        }
        commentsEl.textContent = JSON.stringify(comments);
      });

      const updatedXml = serializer.serializeToString(xmlDoc);

      const res = await fetch(`/api/bpmn/save-edits/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_bpmn_xml: updatedXml }),
      });
      if (!res.ok) throw new Error(`Failed to save BPMN: ${res.status}`);
      toast.success("BPMN and comments saved successfully!");
    } catch (err) {
      console.error(err);
      toast.error("Failed to save BPMN/comments");
    }
  };

  // --- Initialize modeler and import XML ---
  useEffect(() => {
    if (!containerRef.current) return;

    if (!modelerRef.current) {
      modelerRef.current = new BpmnModeler({
        container: containerRef.current,
        width: "100%",
        height: "100%",
        additionalModules: [EmbeddedCommentsModule],
      });
    }

    if (bpmnXml && !loading) {
      (async () => {
        let xmlToImport = bpmnXml;

        if (bpmnXml.includes("<!-- generated by pm4py -->")) {
          xmlToImport = await layoutProcess(bpmnXml);
          await fetch(`/api/bpmn/update-bpmn/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ xml: xmlToImport }),
          });
        }

        const eventBus = modelerRef.current!.get("eventBus") as EventBus;

        const onImportDone = () => {
          requestAnimationFrame(() => {
            setModelImported(true);
            repaintDots();
          });
        };
        const onRenderComplete = () => {
          requestAnimationFrame(() => {
            setModelImported(true);
            repaintDots();
          });
        };
        eventBus.on("import.done", onImportDone);
        eventBus.on("import.render.complete", onRenderComplete);

        await modelerRef.current!.importXML(xmlToImport);

        const canvas = modelerRef.current!.get("canvas") as any;
        canvas.zoom("fit-viewport");

        const logo = containerRef.current?.querySelector(".bjs-powered-by");
        if (logo) (logo as HTMLElement).remove();

        setTimeout(() => setupEmbeddedComments(xmlToImport), 0);

        return () => {
          // @ts-ignore
          eventBus?.off?.("import.done", onImportDone);
          // @ts-ignore
          eventBus?.off?.("import.render.complete", onRenderComplete);
        };
      })();
    }

    return () => {
      removeAllBottleneckDots();
      modelerRef.current?.destroy();
      modelerRef.current = null;
      setModelImported(false);
    };
  }, [bpmnXml, loading, id]);

  // --- BN overlay code (unchanged) ---
  const resolveElementIdsForBN = (bn: BottleneckMetric): string[] => {
    if (!modelerRef.current) return [];
    const elementRegistry = modelerRef.current.get("elementRegistry") as any;
    if (!elementRegistry) return [];

    if ((bn as any).bpmn_element_id) {
      const el = elementRegistry.get((bn as any).bpmn_element_id);
      if (el && (el.type || "").startsWith("bpmn:") && !(el.type || "").toLowerCase().includes("sequenceflow")) {
        return [el.id];
      }
    }

    const all = elementRegistry.getAll?.() || [];
    const nodesByName = new Map<string, any>();
    for (const e of all) {
      const isNode =
        (e.type || "").includes("Task") ||
        (e.type || "").includes("SubProcess") ||
        (e.type || "").includes("Gateway") ||
        (e.type || "").includes("StartEvent") ||
        (e.type || "").includes("EndEvent");
      if (isNode) {
        const name = (e.businessObject?.name || "").trim();
        if (name) nodesByName.set(name, e);
      }
    }

    if ((bn as any).kind === "activity") {
      const targetName = (bn as any).activity?.trim();
      const node = nodesByName.get(targetName);
      return node ? [node.id] : [];
    }

    const sName = (bn as any).source_activity?.trim();
    const tName = (bn as any).target_activity?.trim();
    const src = nodesByName.get(sName);
    const dst = nodesByName.get(tName);
    const ids: string[] = [];
    if (src) ids.push(src.id);
    if (dst && dst.id !== src?.id) ids.push(dst.id);

    if (!ids.length) {
      const flows: any[] = (elementRegistry.filter?.((e: any) => e.type === "bpmn:SequenceFlow") as any[]) || [];
      const flow = flows.find((f) => {
        const srcLabel = f.businessObject?.sourceRef?.name?.trim();
        const dstLabel = f.businessObject?.targetRef?.name?.trim();
        return srcLabel === sName && dstLabel === tName;
      });
      if (flow) {
        const flowSrcId = flow.source?.id || flow.businessObject?.sourceRef?.id;
        const flowDstId = flow.target?.id || flow.businessObject?.targetRef?.id;
        if (flowSrcId) ids.push(flowSrcId);
        if (flowDstId && flowDstId !== flowSrcId) ids.push(flowDstId);
      }
    }

    return ids;
  };

  const bottleneckElementIds = useMemo(() => {
    const ids = new Set<string>();
    if (!modelerRef.current || !effectiveHighlights?.length) return ids;
    for (const bn of effectiveHighlights) {
      for (const id of resolveElementIdsForBN(bn)) ids.add(id);
    }
    return ids;
  }, [effectiveHighlights, bpmnXml]);

  const removeAllBottleneckDots = () => {
    if (!modelerRef.current) return;
    const overlays = modelerRef.current.get("overlays");
    overlayIdsRef.current.forEach((overlayId) => overlays.remove(overlayId));
    overlayIdsRef.current.clear();
  };

  const addDotOverlay = (elementId: string) => {
    if (!modelerRef.current) return;
    const overlays = modelerRef.current.get("overlays");
    const elementRegistry = modelerRef.current.get("elementRegistry");
    const element = elementRegistry.get(elementId);
    if (!element) return;
    if (overlayIdsRef.current.has(elementId)) return;

    const dot = document.createElement("div");
    dot.setAttribute("role", "button");
    dot.title = "View bottlenecks";
    dot.style.width = "10px";
    dot.style.height = "10px";
    dot.style.borderRadius = "9999px";
    dot.style.background = "#ef4444";
    dot.style.boxShadow = "0 0 0 1px white";
    dot.style.cursor = "pointer";
    dot.style.pointerEvents = "auto";
    dot.addEventListener("click", (ev) => {
      ev.stopPropagation();
      setOpenSheet(true);
    });

    const overlayId = overlays.add(element, {
      position: { top: 4, right: 4 },
      html: dot
    });

    overlayIdsRef.current.set(elementId, overlayId);
  };

  const repaintDots = () => {
    if (!modelerRef.current) return;
    removeAllBottleneckDots();
    if (!bottleneckElementIds.size) return;
    bottleneckElementIds.forEach((elId) => addDotOverlay(elId));
  };

  useEffect(() => {
    if (!modelImported) return;
    requestAnimationFrame(() => repaintDots());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelImported, bottleneckElementIds]);

  useEffect(() => {
    if (!modelerRef.current) return;
    if (repaintHandlerAttachedRef.current) return;
    repaintHandlerAttachedRef.current = true;

    const eventBus = modelerRef.current.get("eventBus") as EventBus | undefined;
    if (!eventBus) return;

    const handler = () => repaintDots();
    [
      "import.render.complete",
      "elements.changed",
      "canvas.viewbox.changed",
      "shape.added",
      "shape.removed",
      "commandStack.changed",
    ].forEach((evt) => eventBus.on(evt, handler));

    return () => {
      [
        "import.render.complete",
        "elements.changed",
        "canvas.viewbox.changed",
        "shape.added",
        "shape.removed",
        "commandStack.changed",
      ].forEach((evt) => {
        // @ts-ignore
        eventBus?.off?.(evt, handler);
      });
      repaintHandlerAttachedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!modelImported) return;
    if (!bnFetched) return;
    requestAnimationFrame(() => repaintDots());
  }, [bnFetched, modelImported]);

  // ============================================================================
  // DOWNLOAD HELPERS (robust for both editor mode and read-only mode)
  // ============================================================================

  /** Ensure we have SVG + filename whether or not a live Modeler is present. */
  const getSvgFromEditorOrServer = async (): Promise<{ svg: string; filename: string }> => {
    // 1) If we have a live modeler (edit mode), use it directly.
    if (modelerRef.current) {
      const { svg } = await modelerRef.current.saveSVG();
      return { svg, filename: bpmnName || "bpmn-diagram" };
    }

    // 2) Fallback (read-only / Approved): fetch XML and render offscreen with Viewer
    const res = await fetch(`/api/bpmn/export-svg/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch BPMN XML (${res.status})`);
    const data = await res.json();

    const BpmnViewer = (await import("bpmn-js/lib/NavigatedViewer")).default;
    const temp = document.createElement("div");
    temp.style.position = "absolute";
    temp.style.left = "-9999px";
    temp.style.top = "0";
    temp.style.width = "1200px";
    temp.style.height = "900px";
    document.body.appendChild(temp);

    const viewer = new BpmnViewer({ container: temp, width: 1200, height: 900 });
    await viewer.importXML(data.xml);
    const { svg } = await viewer.saveSVG();
    viewer.destroy();
    temp.remove();

    return { svg, filename: data.filename || "bpmn-diagram" };
  };

  const handleExportSvg = async () => {
    try {
      const { svg, filename } = await getSvgFromEditorOrServer();
      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename}.svg`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("SVG exported successfully!");
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Failed to export SVG");
    }
  };

  const handleExportPng = async () => {
    try {
      const { svg, filename } = await getSvgFromEditorOrServer();

      const img = new Image();
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas context error");

      img.onload = () => {
        const padding = 40;
        (canvas as any).width = (img as any).width + padding * 2;
        (canvas as any).height = (img as any).height + padding * 2;
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, (canvas as any).width, (canvas as any).height);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(img, padding, padding);
        canvas.toBlob((blob) => {
          if (!blob) return;
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${filename}.png`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
          toast.success("PNG exported successfully!");
        }, "image/png");
      };
      img.onerror = () => toast.error("Failed to load SVG for PNG conversion");
      img.src = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Failed to export PNG");
    }
  };

  const handleDownloadBpmn = async () => {
    try {
      const res = await fetch(`/api/bpmn/download/${id}`, { credentials: "include" });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${bpmnName || "bpmn-diagram"}.bpmn`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("BPMN downloaded successfully!");
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Failed to download BPMN");
    }
  };

  // --- UI ---
  return (
    <div className="editor-container mt-2">
      <div className="flex flex-row justify-between items-center">
        {projectId && (
          <div>
            {(user?.email === bpo?.email) && (approvalStatus === "Pending") ? (
              <div className="flex flex-row gap-2">
                <Button className="bg-emerald-500 hover:bg-emerald-700" onClick={() => openDecisionModal("approved")}><Check /> Approve</Button>
                <Button className="bg-red-500 hover:bg-red-700" onClick={() => openDecisionModal("rejected")}><X /> Reject</Button>
              </div>
            ) : (
              <div className="flex flex-row gap-2 items-center">
                <div className="font-medium">Approval Status: </div>
                <div className={`py-1 px-2 rounded-lg text-white ${approvalStatus === "Approved" ? "bg-emerald-500" : approvalStatus === "Rejected" ? "bg-red-500" : "bg-gray-500"}`}>{approvalStatus}</div>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col items-center">
          <p className="font-semibold text-2xl">{bpmnName} (v{bpmnVersion})</p>
          <p className="mb-5">{bpmnDescription}</p>
        </div>

        <div className="flex flex-row gap-2">
          <Button onClick={handleSaveBpmn}>Save</Button>

          {/* Bottlenecks side panel */}
          <Sheet open={openSheet} onOpenChange={setOpenSheet}>
            <SheetTrigger asChild>
              <Button
                variant="default"
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                disabled={!projectId || !effectiveHighlights?.length}
                title={
                  !projectId
                    ? "Project id missing"
                    : !effectiveHighlights?.length
                    ? "No significant bottlenecks detected"
                    : "View Top 10% bottlenecks"
                }
              >
                Bottlenecks
                {effectiveHighlights?.length ? (
                  <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded bg-background/30 px-1 text-[10px] font-semibold text-primary-foreground">
                    {effectiveHighlights.length}
                  </span>
                ) : null}
              </Button>
            </SheetTrigger>

            <SheetContent side="right" className="w-[420px]">
              <SheetHeader>
                <SheetTitle>Top 10% Bottlenecks</SheetTitle>
              </SheetHeader>

              {!projectId || !effectiveHighlights?.length ? (
                <div className="text-sm text-muted-foreground mt-2">
                  No significant bottlenecks.
                </div>
              ) : (
                <div className="mt-2 space-y-2">
                  {effectiveHighlights.map((bn) => {
                    const title =
                      bn.kind === "activity"
                        ? `Activity: ${(bn as any).activity}`
                        : `Transition: ${(bn as any).source_activity} → ${(bn as any).target_activity}`;
                    const path = makeRecommendationPath(projectId!, bn);
                    return (
                      <Link
                        key={`${bn.kind}-${(bn as any).id ?? `${(bn as any).source_activity}-${(bn as any).target_activity}`}`}
                        to={path}
                        className="flex items-center justify-between rounded border p-3 hover:bg-primary/5 transition"
                        onClick={() => setOpenSheet(false)}
                      >
                        <div className="flex flex-col">
                          <span className="font-semibold text-primary">{title}</span>
                          <span className="text-xs text-muted-foreground">
                            90th percentile: {formatDurationSec((bn as any).p90_seconds)} · Occurrences: {(bn as any).count}
                          </span>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </Link>
                    );
                  })}
                </div>
              )}
            </SheetContent>
          </Sheet>

          {/* Submit for Approval Button (Conditional) */}
          {projectId && userRole === 'admin' && (
            <Button onClick={handleSubmitForApproval} disabled={!bpo}>
              <Send className="h-4 w-4 mr-2" />
              Submit for Approval
            </Button>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                Download <ChevronDown className="ml-1 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleExportSvg}>Download as SVG</DropdownMenuItem>
              <DropdownMenuItem onClick={handleExportPng}>Download as PNG</DropdownMenuItem>
              <DropdownMenuItem onClick={handleDownloadBpmn}>Download as BPMN</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {projectId && (user?.email === bpo?.email) && (
            <Button onClick={() => setIsRestoreModalOpen(true)}>
              <History className="h-4 w-4 mr-2" />
              Restore
            </Button>
          )}
        </div>
      </div>

      {/* Restore Version Modal */}
      <RestoreVersionModal
        isOpen={isRestoreModalOpen}
        onClose={() => setIsRestoreModalOpen(false)}
        bpmnId={id}
        projectId={projectId}
        currentVersion={parseFloat(bpmnVersion) || 1}
        onRestored={handleVersionRestored}
      />

      {/* Approval Modal */}
      <ApprovalModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        selectedRequest={selectedRequest}
        decision={selectedDecision}
        onConfirm={handleConfirmDecision}
      />

      {error && <p className="text-red-500">Failed to load BPMN: {error}</p>}

      <div
        ref={containerRef}
        id="canvas"
        className="w-full h-[80vh] border border-black relative overflow-visible"
      />
    </div>
    
  );
}
