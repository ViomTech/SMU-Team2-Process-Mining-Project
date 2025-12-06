import { useState, useEffect } from "react";
import { fetchBpmnXml } from "@/utils/BpmnApi";

export const useBpmnXml = (id: number) => {
    const [bpmnXml, setBpmnXml] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        const loadXml = async () => {
            setLoading(true);
            setError(null);

            try {
                const xml = await fetchBpmnXml(id);
                setBpmnXml(xml);

            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load BPMN");
                
            } finally {
                setLoading(false);
            }
        };

        loadXml();
    }, [id]);

    return { bpmnXml, loading, error };
}