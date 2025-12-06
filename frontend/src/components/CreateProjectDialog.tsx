import { useState, useEffect } from "react";
import { createProject, getBPOusers } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { PlusCircle } from "lucide-react";
// Make sure you've added the select component via shadcn CLI
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface User {
  user_id: number;
  name: string;
}

interface CreateProjectProps {
  triggerElement?: React.ReactNode;
  onProjectCreated: () => void; // Callback to refresh the project list
}

export default function CreateProjectDialog({ triggerElement, onProjectCreated }: CreateProjectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [selectedBpoId, setSelectedBpoId] = useState<number | null>(null);

  // Fetch the user list when the dialog opens
  useEffect(() => {
    if (isOpen) {
      const fetchBPOusers = async () => {
        try {
          // 3. Call the renamed function
          const userList = await getBPOusers();
          setUsers(userList);
        } catch (error) {
          toast.error("Could not load BPO user list.");
        }
      };
      fetchBPOusers();
    }
  }, [isOpen]);

  const handleCreateProject = async () => {
    // Block submission if no BPO is selected
    if (!selectedBpoId) {
      toast.error("Please assign a BPO before creating the project.");
      return;
    }

    try {
      await createProject(projectName, projectDescription, selectedBpoId);
      toast.success("Project created successfully.");
      
      setIsOpen(false);
      setProjectName("");
      setProjectDescription("");
      setSelectedBpoId(null);
      onProjectCreated(); // Trigger the refresh in the parent component
      
    } catch (err: any) {
      toast.error(`Failed to create project: ${err.message}`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {triggerElement || (
          <Button>
            <PlusCircle className="h-4 w-4 mr-2" />
            Create Project
          </Button>
        )}
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Process</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="name" className="text-right">Name</Label>
            <Input id="name" value={projectName} onChange={(e) => setProjectName(e.target.value)} className="col-span-3" />
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="description" className="text-right">Description</Label>
            <Textarea id="description" value={projectDescription} onChange={(e) => setProjectDescription(e.target.value)} className="col-span-3" />
          </div>

          {/* New BPO dropdown menu */}
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="bpo" className="text-right">Assign BPO</Label>
            <Select onValueChange={(value) => setSelectedBpoId(Number(value))}>
              <SelectTrigger className="col-span-3">
                <SelectValue placeholder="Select a business process owner..." />
              </SelectTrigger>
              <SelectContent>
                {users.map((user) => (
                  <SelectItem key={user.user_id} value={String(user.user_id)}>
                    {user.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleCreateProject}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}