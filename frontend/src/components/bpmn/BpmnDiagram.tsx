import { useState, useRef, useEffect } from "react";
import BpmnViewer from "bpmn-js/lib/NavigatedViewer";
import { useBpmnXml } from "@/hooks/useBpmnXml";

type props = {
  id: number,
  height?: number | string
}

export default function BpmnDiagram({ id, height }: props) {
  const { bpmnXml, loading, error } = useBpmnXml(id);
  const [renderingError, setRenderingError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<BpmnViewer | null>(null);

  useEffect(() => {
    if (bpmnXml && containerRef.current && !loading) {
      if (viewerRef.current) {
        viewerRef.current.destroy();
      }

      const viewer = new BpmnViewer({
                      container: containerRef.current,
                      height: height,
                      width: "100%"
                  });

      viewerRef.current = viewer;

      viewer.importXML(bpmnXml)
        .then(() => {
          const canvas = viewer.get("canvas") as any;
          canvas.zoom("fit-viewport");

          const logo = containerRef.current?.querySelector(".bjs-powered-by");
          if (logo) logo.remove();

          setRenderingError(null); 
        })
        .catch((err: Error) => {
          console.error("BPMN rendering error:", err);
          console.error("Error details:", err.message);
          setRenderingError(`Failed to render BPMN: ${err.message}`);
        });
    }

    return () => {
        if (viewerRef.current) {
            viewerRef.current.destroy();
            viewerRef.current = null;
        }
    };
  }, [bpmnXml, loading]);
  
  if (loading) return <div className="p-8 text-center">Loading BPMN...</div>;
  if (error || renderingError) return <div className="p-8 text-center text-red-500">Error: {error || renderingError}</div>;
  if (!bpmnXml) return <div className="p-8 text-center">No BPMN data available</div>

  return (
    <div className="bpmn-diagram">
      <div 
          ref={containerRef} 
          className="bpmn-container w-full h-full border border-gray-500 rounded relative"
          style={{
              height: typeof height === "number" ? `${height}` : height
          }}
      ></div>
    </div>
  );
}