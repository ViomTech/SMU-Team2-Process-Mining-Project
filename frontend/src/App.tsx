// src/App.tsx
import { Routes, Route } from "react-router-dom";
import Homepage from "@/pages/Homepage";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import { Toaster } from "sonner";
import { RequireAuth, RedirectIfAuthed } from "@/components/auth-guards";
import Register from "@/pages/Register";
import { useLocation } from "react-router-dom";
import NavBar from "@/components/NavBar";
import FilesDashboard from "@/pages/FilesDashboard";
import Dashboard from "@/pages/Dashboard";
import { AuthProvider } from "@/contexts/AuthContext";
import BpmnView from "@/pages/BpmnView";
import BpmnLibrary from "@/pages/BpmnLibrary";
import NotificationsPage from "@/pages/Notifications";
import ProjectsDashboard from "@/pages/ProjectsDashboard";
import RecommendationView from "@/pages/RecommendationView";
import RecommendationLibrary from "@/pages/RecommendationLibrary";
import ApprovalsPage from "@/pages/BpoApproval";

// NEW: React Query + Dashboards page
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MetricsDashboard from "@/pages/MetricsDashboard";

const queryClient = new QueryClient();

export default function App() {
  const location = useLocation();
  const hideNavbarOn = ["/login", "/forgot-password", "/reset-password", "/register"];
  const showNavbar = !hideNavbarOn.includes(location.pathname);

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <div>
          {showNavbar && <NavBar />}
          {showNavbar && <div className="h-16 pt-[env(safe-area-inset-top)]" aria-hidden />}

          <Routes>
            {/* Home (protected) */}
            <Route
              path="/"
              element={
                <RequireAuth>
                  <Homepage />
                </RequireAuth>
              }
            />

            {/* Existing ingestion dashboard */}
            <Route
              path="/ingestion-dashboard"
              element={
                <RequireAuth>
                  <Dashboard />
                </RequireAuth>
              }
            />

            {/* Projects */}
            <Route
              path="/projects"
              element={
                <RequireAuth>
                  <ProjectsDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/projects/:projectId"
              element={
                <RequireAuth>
                  <FilesDashboard />
                </RequireAuth>
              }
            />

            {/* Notifications */}
            <Route
              path="/notifications"
              element={
                <RequireAuth>
                  <NotificationsPage />
                </RequireAuth>
              }
            />

            {/* BPMN */}
            <Route
              path="/bpmn/view/:id"
              element={
                <RequireAuth>
                  <BpmnView />
                </RequireAuth>
              }
            />
            <Route
              path="/bpmn/view-all"
              element={
                <RequireAuth>
                  <BpmnLibrary />
                </RequireAuth>
              }
            />

            {/* Recommendations */}
            <Route
              path="/recommendation/view-all"
              element={
                <RequireAuth>
                  <RecommendationLibrary />
                </RequireAuth>
              }
            />
            <Route
              path="/projects/:projectId/recommendation/:bottleneckId"
              element={
                <RequireAuth>
                  <RecommendationView />
                </RequireAuth>
              }
            />

            {/* Approvals */}
            <Route
              path="/approvals"
              element={
                <RequireAuth>
                  <ApprovalsPage />
                </RequireAuth>
              }
            />

            {/* NEW: Dashboards route */}
            <Route
              path="/dashboards"
              element={
                <RequireAuth>
                  <MetricsDashboard />
                </RequireAuth>
              }
            />

            {/* Auth */}
            <Route
              path="/login"
              element={
                <RedirectIfAuthed>
                  <Login />
                </RedirectIfAuthed>
              }
            />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/register" element={<Register />} />
          </Routes>

          <Toaster richColors closeButton />
        </div>
      </QueryClientProvider>
    </AuthProvider>
  );
}
