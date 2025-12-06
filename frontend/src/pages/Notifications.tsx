// src/pages/Notifications.tsx
import { Link, useSearchParams } from "react-router-dom";
import { useMemo, useState, useEffect } from "react";

type NotificationType = "Login Events" | "Recommendations" | "Validations";

type AppNotification = {
  id: number | string;
  type: NotificationType;
  message: string;
  timestamp: string;   // ISO string
  targetUrl: string;
  read: boolean;
};

const CATEGORIES: Array<"All" | NotificationType> = [
  "All",
  "Login Events",
  "Recommendations",
  "Validations",
];

function formatFullTimestamp(iso?: string): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString("en-US", {
      month: "short",   // Sep
      day: "numeric",   // 10
      year: "numeric",  // 2025
      hour: "numeric",
      minute: "2-digit",
      hour12: true,     // 3:40 PM
    });
  }

export default function NotificationsPage() {
  const [data, setData] = useState<AppNotification[] | null>(null); // null = loading
  const [error, setError] = useState<string | null>(null);

  // Query params: ?cat=Recommendations&unread=1
  const [search, setSearch] = useSearchParams();
  const initialCat = (search.get("cat") as NotificationType) ?? "All";
  const initialUnread = search.get("unread") === "1";

  const [cat, setCat] = useState<"All" | NotificationType>(
    CATEGORIES.includes(initialCat as any) ? (initialCat as any) : "All"
  );
  const [unreadOnly, setUnreadOnly] = useState<boolean>(initialUnread);

  // ---- Load from backend ----
 // ---- Load from backend (defensive) ----
useEffect(() => {
    let cancelled = false;
  
    (async () => {
      try {
        setError(null);
        const res = await fetch("/api/notifications", { credentials: "include" });
  
        // Read as text first so we can log/parse safely even if it's HTML
        const raw = await res.text();
  
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ${res.statusText}: ${raw.slice(0,200)}`);
        }
  
        let parsed: any;
        try {
          parsed = raw ? JSON.parse(raw) : [];
        } catch {
          // 200 but not JSON (often proxying index.html) -> surface exact body
          throw new Error(`Non-JSON 200 from /api/notifications: ${raw.slice(0,200)}`);
        }
  
        // Accept array OR {data: [...]}
        const arr: any[] = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.data) ? parsed.data : [];
        // Normalize snake_case/camelCase
        const normalized: AppNotification[] = arr.map((n) => ({
          id: n.id ?? n.notification_id ?? crypto.randomUUID(),
          type: (n.type ?? "Recommendations") as NotificationType,
          message: n.message ?? "",
          timestamp: n.timestamp ?? n.created_at ?? new Date().toISOString(),
          targetUrl: n.targetUrl ?? n.target_url ?? "/",
          read: Boolean(n.read),
        }));
  
        if (!cancelled) setData(normalized);
      } catch (e: any) {
        if (!cancelled) {
          console.error("Notifications load error:", e);
          setError(e?.message || "Failed to load notifications.");
          setData([]); // show empty state instead of spinner
        }
      }
    })();
  
    return () => { cancelled = true; };
  }, []);
  

  // Keep URL in sync when user changes filters
  useEffect(() => {
    const next = new URLSearchParams(search);
    if (cat === "All") next.delete("cat");
    else next.set("cat", cat);
    if (unreadOnly) next.set("unread", "1");
    else next.delete("unread");
    setSearch(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cat, unreadOnly]);

  // Counts per category (for tab badges)
  const counts = useMemo(() => {
    const base = {
      All: data?.length ?? 0,
      "Login Events": 0,
      Recommendations: 0,
      Validations: 0,
    } as Record<"All" | NotificationType, number>;
    (data ?? []).forEach((n) => (base[n.type] += 1));
    return base;
  }, [data]);

  // Filtered items for current view
  const items = useMemo(() => {
    const listBase = data ?? [];
    let list = cat === "All" ? listBase : listBase.filter((n) => n.type === cat);
    if (unreadOnly) list = list.filter((n) => !n.read);
    return [...list].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [data, cat, unreadOnly]);

  // --- Mark read (optional backend persistence) ---
  const markAllAsRead = async () => {
    // optimistic UI
    setData((prev) => (prev ? prev.map((n) => ({ ...n, read: true })) : prev));
    // try to persist (ignore failure silently for now)
    try {
      await fetch("/api/notifications/mark-all-read", {
        method: "PATCH",
        credentials: "include",
      });
    } catch {}
  };

  const markOneAsRead = async (id: number | string) => {
    setData((prev) => (prev ? prev.map((n) => (n.id === id ? { ...n, read: true } : n)) : prev));
    try {
      await fetch(`/api/notifications/${id}/read`, {
        method: "PATCH",
        credentials: "include",
      });
    } catch {}
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
            />
            Unread only
          </label>
          <button
            onClick={markAllAsRead}
            className="text-sm px-3 py-1.5 rounded-lg border hover:bg-gray-50"
          >
            Mark all as read
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCat(c)}
            className={`px-3 py-1.5 rounded-lg text-sm border relative ${
              cat === c ? "bg-gray-900 text-white border-gray-900" : "hover:bg-gray-50"
            }`}
          >
            {c}
            <span className={`ml-1 text-xs ${cat === c ? "opacity-90" : "opacity-70"}`}>
              ({counts[c] ?? 0})
            </span>
          </button>
        ))}
      </div>

      {/* Body */}
      {data === null ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : error ? (
        <div className="text-sm text-red-600">{error}</div>
      ) : items.length === 0 ? (
        <div className="border rounded-xl p-10 text-center text-gray-500">
          You’re all caught up.
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li
              key={n.id}
              className={`border rounded-xl p-4 ${!n.read ? "bg-amber-50 border-amber-200" : "bg-white"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500">{n.type}</div>
                  <div className={`mt-0.5 ${!n.read ? "font-semibold" : ""}`}>
                    {n.message}
                    {(() => {
                        const prettyTs = formatFullTimestamp(n.timestamp);
                        return prettyTs ? ` on ${prettyTs}` : "";
                    })()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!n.read && (
                    <button
                      onClick={() => markOneAsRead(n.id)}
                      className="text-sm px-2 py-1 rounded-lg border hover:bg-gray-50"
                    >
                      Mark read
                    </button>
                  )}
                  <Link
                    to={n.targetUrl}
                    className="text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:opacity-90"
                  >
                    Open
                  </Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
