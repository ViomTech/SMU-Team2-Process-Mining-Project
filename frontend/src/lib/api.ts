// src/lib/api.ts
export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:5000";

export async function getMe() {
  const res = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}

export async function logout() {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
}

export async function getDashboardData() {
  const res = await fetch(`${API_URL}/api/dashboard/dashboard-data`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch dashboard data.");
  return res.json();
}

export async function getProjects() {
  const res = await fetch(`${API_URL}/api/project/get-projects`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch projects.");
  return res.json();
}

export async function updateProject(project_id: number, data: any) {
  const res = await fetch(`${API_URL}/api/project/update-project-info/${project_id}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update project.");
  return res.json();
}

export async function deleteProject(project_id: number) {
  const res = await fetch(`${API_URL}/api/project/delete-project/${project_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to delete project.");
  return res.json();
}

export async function getRecentProjects() {
  const res = await fetch(`${API_URL}/api/project/get-recent-projects`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch projects.");
  return res.json();
}

export async function getProjectById(projectId: string) {
  const res = await fetch(`${API_URL}/api/project/${projectId}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch project details.");
  return res.json();
}

// ## THIS FUNCTION WAS UPDATED ##
// It now accepts assignedBpoId and sends it to the backend.
export async function createProject(
  name: string,
  description: string,
  assignedBpoId: number | null
) {
  const res = await fetch(`${API_URL}/api/project/create-project`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, assigned_bpo_id: assignedBpoId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to create project.");
  }
  return res.json();
}

export async function getRecommendation() {
  const res = await fetch(`${API_URL}/api/recommendation/library`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to fetch recommendations.");
  }
  return res.json();
}

// It fetches the list of users for the BPO dropdown menu.
export async function getBPOusers() {
  const res = await fetch(`${API_URL}/api/user/list`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch users");
  return res.json();
}

export type NotificationType = "Login Events" | "Recommendations" | "Validations";

export type AppNotification = {
  id: number | string;
  type: NotificationType;
  message: string;
  timestamp: string; // ISO string from backend
  targetUrl: string;
  read: boolean;
};

export async function getNotifications(): Promise<AppNotification[]> {
  // ✅ fixed: now uses API_URL
  const res = await fetch(`${API_URL}/api/notifications`, { credentials: "include" });
  if (!res.ok) throw new Error(`Failed to fetch notifications: ${res.status}`);
  return res.json();
}

export async function deleteRecommendation(recommendationId: string) {
  const res = await fetch(`${API_URL}/api/recommendation/delete`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recommendation_id: recommendationId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to delete recommendation.");
  }
  return res.json();
}

export async function submitForApproval(bpmnId: number, bpoId: number) {
  const res = await fetch(`${API_URL}/api/bpmn/submit-for-approval`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bpmn_id: bpmnId, bpo_id: bpoId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: "Failed to submit for approval." }));
    throw new Error(errorData.error || `HTTP error ${res.status}`);
  }
  return res.json();
}
