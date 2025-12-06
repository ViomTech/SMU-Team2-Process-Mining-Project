import { useDropzone } from "react-dropzone";
import { Input } from "@/components/ui/input";
import { Upload } from 'lucide-react';

interface DropzoneProps {
    onFileSelected: (file: File) => void
}

export default function BpmnDropzone({ onFileSelected }: DropzoneProps) {
    const {acceptedFiles, getRootProps, getInputProps} = useDropzone({
        accept: {
            "application/xml": [".bpmn", ".xml"]
        },
        multiple: false,
        onDrop: (files) => {
            if (files.length > 0) onFileSelected(files[0]);
        }
    });

    return (
        <div className="mt-3 w-full">
            <div className="flex flex-col justify-center items-center">
                <div className="flex flex-col w-full px-10 py-8 border-gray-400 outline-dashed rounded-sm items-center">
                    <div {...getRootProps({className: "dropzone"})}>
                        <Input {...getInputProps()} />
                        <div className="flex flex-row gap-2 text-gray-400 items-center">
                            <Upload />
                            Drop items here, or click to browse files.
                        </div>
                    </div>
                </div>

                {acceptedFiles.length > 0 && (
                <div className="mt-2 w-full text-left self-start">
                    Selected File: <span>{acceptedFiles[0].name}</span>
                </div>
                )}
            </div>
        </div>
    )
}