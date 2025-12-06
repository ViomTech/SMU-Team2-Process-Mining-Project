export const fetchBpmnXml = async (id: number): Promise<string> => {
    
    const res = await fetch(`/api/bpmn/view/${id}`);

    if (!res.ok) {
        throw new Error(`Failed to fetch BPMN: ${res.status}`);
    }

    const xml = await res.text();
    console.log('Raw XML response:', xml.substring(0, 300));
    console.log('XML length:', xml.length);
    
    return xml;
}