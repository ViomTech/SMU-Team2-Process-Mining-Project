// ProjectsDashboard.tsx
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { getProjects, updateProject, deleteProject  } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { EllipsisVertical } from "lucide-react";
import { toast } from "sonner";

interface Project {
  project_id: number;
  project_name: string;
  assigned_bpo: string;
  description: string;
  created_at: string;
  version: number;
  last_modified: string;
  approval_status: string;
}

const statusVariantMap: Record<string, string> = {
  Approved: "bg-emerald-500 text-white",
  Pending: "bg-gray-500 text-white",
  Rejected: "bg-red-500 text-white",
  "Not Submitted": "bg-gray-200 text-gray-800 hover:bg-gray-200"
};

export default function ProjectsDashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [openEdit, setOpenEdit] = useState(false);
  const [openDelete, setOpenDelete] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await getProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch projects");
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch projects when the component loads
  useEffect(() => {
    fetchProjects();
  }, []);

  const handleOpenEdit = (project: Project) => {
    setSelectedProject(project);
    setEditName(project.project_name);
    setEditDescription(project.description || "");
    setOpenEdit(true);
  };

  const handleUpdateProject = async () => {
    if (!selectedProject) return;
    try {
      await updateProject(selectedProject.project_id, {
        project_name: editName,
        description: editDescription,
      });
      toast.success("Project updated successfully!");
      setOpenEdit(false);
      fetchProjects();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to update project.");
    }
  };

  const handleOpenDelete = (project: Project) => {
    setSelectedProject(project);
    setOpenDelete(true);
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;
    try {
      await deleteProject(selectedProject.project_id);
      toast.success("Project deleted successfully!");
      setOpenDelete(false);
      fetchProjects();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to delete project.");
    }
  };

  if (loading) return <div className="p-8 text-center">Loading Projects...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  return (
    <main className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
      <p className="text-2xl font-semibold">Project Overview</p>

      <div className="grid gap-4 md:grid-cols-2 md:gap-8 lg:grid-cols-3">
        {projects.length > 0 ? (
          projects.map((project) => (
            <Link to={`/projects/${project.project_id}`} key={project.project_id}>
            <Card key={project.project_id} className="relative hover:bg-accent cursor-pointer">
              <div className="absolute top-4 right-4 flex gap-2">
                <Badge className={`${statusVariantMap[project.approval_status] || "bg-gray-400 text-white"}`}>
                  {project.approval_status}
                </Badge>
                {project.version && <Badge variant="secondary">v{project.version.toFixed(1)}</Badge>}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <EllipsisVertical />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => handleOpenEdit(project)}>Edit</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleOpenDelete(project)}>Delete</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <CardHeader className="flex flex-row justify-between">
                <div>
                  <CardTitle>{project.project_name}</CardTitle>
                  <CardDescription className="line-clamp-2">{project.description || "No description provided."}</CardDescription>
                </div>

              </CardHeader>

              <CardContent>
                <p className="text-sm text-muted-foreground">Assigned to: {project.assigned_bpo}</p>
                <p className="text-sm text-muted-foreground">Created on: {new Date(project.created_at).toLocaleDateString()}</p>
                <p className="text-sm text-muted-foreground">Last modified: {new Date(project.last_modified).toLocaleDateString()}</p>
              </CardContent>
            </Card>
            </Link>
          ))
        ) : (
          <p>No projects found. Create one to get started!</p>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={openEdit} onOpenChange={setOpenEdit}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>Update the project name and description.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="project-name">Name</Label>
              <Input id="project-name" value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="project-desc">Description</Label>
              <Textarea id="project-desc" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setOpenEdit(false)}>Cancel</Button>
            <Button onClick={handleUpdateProject}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={openDelete} onOpenChange={setOpenDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this project? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setOpenDelete(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteProject}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}