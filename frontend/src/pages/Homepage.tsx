import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import CreateProjectDialog from "@/components/CreateProjectDialog";
import UploadBpmn from "@/components/bpmn/UploadBpmn";
import RecentProjects from "@/components/RecentProjects";
import RecentBpmn from "@/components/bpmn/RecentBpmn";
import { Button } from "@/components/ui/button";
import bpmnUpload from "@/assets/bpmn-upload.png";
import createProject from "@/assets/create-project.png";

export default function Homepage() {
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);
  const [userName, setUserName] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("");

  const handleProjectCreated = () => setRefreshKey((k) => k + 1);

  // Fetch logged-in user info from /auth/me
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await fetch("/auth/me", {
          credentials: "include",
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data?.name) setUserName(data.name);
        if (data?.role) {
          // Capitalize first letter for aesthetics
          const role =
            data.role === "business process owner"
              ? "BPO"
              : data.role.charAt(0).toUpperCase() + data.role.slice(1);
          setUserRole(role);
        }
      } catch (e) {
        console.error("Failed to load user info:", e);
      }
    };
    fetchUser();
  }, []);

  return (
    <div className="page mt-4">
      <div className="flex flex-col px-8">
        <div className="flex flex-row justify-between items-center">
          <p className="text-3xl font-medium">
            Welcome to ProcessPilot,
            {userName && (
              <span className="text-gray-800 font-semibold">
                {" "}
                {userName}
                {userRole && (
                  <span className="text-gray-600 font-normal">
                    {" "}
                    ({userRole})
                  </span>
                )}
              </span>
            )}
          </p>
        </div>

        <p className="mt-2 text-gray-600">
          Discover, analyze, and optimize your business processes effortlessly.
          Our platform turns complex workflows into actionable insights, helping
          you streamline operations, reduce bottlenecks, and maximize
          efficiency.
        </p>
      </div>

      <div className="flex flex-col gap-2 bg-gray-100 py-4 px-8 mt-3 min-h-[77vh]">
        <div className="first-section">
          <p className="text-lg font-medium pl-2">Get Started</p>

          <div className="flex flex-row gap-4 mt-2">
            <CreateProjectDialog
              onProjectCreated={handleProjectCreated}
              triggerElement={
                <button className="bg-white w-[480px] p-3 rounded-sm">
                  <div className="flex flex-row gap-2 text-left items-center">
                    <img src={createProject} className="h-16 w-16" />
                    <div>
                      <p className="font-medium text-base">
                        Create a New Process Analysis
                      </p>
                      <p className="text-gray-600 text-sm">
                        Organize your event logs and workflows for analysis.
                      </p>
                    </div>
                  </div>
                </button>
              }
            />

            <UploadBpmn
              triggerElement={
                <button className="bg-white w-[480px] p-3 rounded-sm">
                  <div className="flex flex-row gap-2 text-left items-center">
                    <img src={bpmnUpload} className="h-16 w-16" />
                    <div>
                      <p className="font-medium text-base">
                        Upload a BPMN diagram
                      </p>
                      <p className="text-gray-600 text-sm">
                        Upload your BPMN diagrams to view, edit, and manage them
                        online.
                      </p>
                    </div>
                  </div>
                </button>
              }
            />
          </div>
        </div>

        <div className="second-section mt-4">
          <div className="flex flex-row justify-between">
            <p className="text-lg font-medium pl-2">Recent Processes</p>
            <Button onClick={() => navigate("/projects")}>View All</Button>
          </div>
          <RecentProjects key={refreshKey} />
        </div>

        <div className="third-section mt-4">
          <div className="flex flex-row justify-between">
            <p className="text-lg font-medium pl-2">Recent BPMNs</p>
            <Button onClick={() => navigate("/bpmn/view-all")}>View All</Button>
          </div>

          <RecentBpmn />
        </div>
      </div>
    </div>
  );
}
