// src/components/NavBar.tsx
import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import BrandLogo from "@/components/BrandLogo";

type Notification = {
  id: number;
  type: string;
  message: string;
  timestamp: string;
  targetUrl: string;
  read: boolean;
};

export default function NavBar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch("/api/notifications", { credentials: "include" });
        if (!res.ok) return;
        const data: Notification[] = await res.json();
        if (mounted) setUnread(data.filter((n) => !n.read).length);
      } catch {}
    };
    load();
    const id = setInterval(load, 30000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="fixed left-0 right-0 top-0 z-50 border-b bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="w-full px-4 md:px-6">
        <div className="flex h-16 w-full items-center">
          <BrandLogo size={28} withText className="shrink-0 select-none" />
          <nav aria-label="Primary" className="ml-auto">
            <ul className="flex items-center gap-8">
              <li>
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `text-sm font-medium transition hover:opacity-80 ${isActive ? "opacity-100" : "opacity-80"}`
                  }
                >
                  Home
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/projects"
                  end
                  className={({ isActive }) =>
                    `text-sm font-medium transition hover:opacity-80 ${isActive ? "opacity-100" : "opacity-80"}`
                  }
                >
                  Processes
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/bpmn/view-all"
                  end
                  className={({ isActive }) =>
                    `text-sm font-medium transition hover:opacity-80 ${isActive ? "opacity-100" : "opacity-80"}`
                  }
                >
                  My BPMNs
                </NavLink>
              </li>

              {/* NEW: Dashboards */}
              <li>
                <NavLink
                  to="/dashboards"
                  className={({ isActive }) =>
                    `text-sm font-medium transition hover:opacity-80 ${isActive ? "opacity-100 font-semibold" : "opacity-80"}`
                  }
                >
                  Dashboards
                </NavLink>
              </li>

              {user?.role === "business process owner" && (
                <li>
                  <NavLink
                    to="/approvals"
                    className={({ isActive }) =>
                      `text-sm font-medium transition hover:opacity-80 ${
                        isActive ? "opacity-100 font-semibold" : "opacity-80"
                      }`
                    }
                  >
                    Approvals
                  </NavLink>
                </li>
              )}

              <li>
                <NavLink
                  to="/recommendation/view-all"
                  className={({ isActive }) =>
                    `relative inline-flex items-center text-sm font-medium transition hover:opacity-80 ${
                      isActive ? "opacity-100" : "opacity-80"
                    }`
                  }
                >
                  Recommendations
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/notifications"
                  className={({ isActive }) =>
                    `relative inline-flex items-center text-sm font-medium transition hover:opacity-80 ${
                      isActive ? "opacity-100" : "opacity-80"
                    }`
                  }
                >
                  Notifications
                  {unread > 0 && (
                    <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
                      {unread}
                    </span>
                  )}
                </NavLink>
              </li>
              <li>
                <button onClick={handleLogout} className="text-sm font-medium transition hover:opacity-80">
                  Logout
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
      <div className="pt-[env(safe-area-inset-top)]" />
    </header>
  );
}
