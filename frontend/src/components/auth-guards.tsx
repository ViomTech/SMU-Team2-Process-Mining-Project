// src/components/auth-guards.tsx
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getMe } from "@/lib/api";

type GateState = "loading" | "authed" | "anon";

export function RequireAuth({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>("loading");

  useEffect(() => {
    let mounted = true;
    (async () => {
      const me = await getMe();
      if (!mounted) return;
      setState(me ? "authed" : "anon");
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (state === "loading") return <div style={{ padding: 24 }}>Checking session…</div>;
  if (state === "anon") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>("loading");

  useEffect(() => {
    let mounted = true;
    (async () => {
      const me = await getMe();
      if (!mounted) return;
      setState(me ? "authed" : "anon");
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (state === "loading") return <div style={{ padding: 24 }}>Loading…</div>;
  if (state === "authed") return <Navigate to="/" replace />;
  return <>{children}</>;
}
