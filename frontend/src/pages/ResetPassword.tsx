// src/pages/ResetPassword.tsx
import * as React from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, Link, useLocation } from "react-router-dom";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";

const ResetSchema = z.object({
  password: z.string().min(3, "At least 3 characters"),
  confirm: z.string().min(3, "At least 3 characters"),
}).refine((vals) => vals.password === vals.confirm, {
  message: "Passwords do not match",
  path: ["confirm"],
});

type ResetValues = z.infer<typeof ResetSchema>;
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function ResetPassword() {
  const [submitting, setSubmitting] = React.useState(false);
  const navigate = useNavigate();
  const { search } = useLocation();
  const token = new URLSearchParams(search).get("token") || "";

  const form = useForm<ResetValues>({
    resolver: zodResolver(ResetSchema),
    defaultValues: { password: "", confirm: "" },
  });

  async function onSubmit(values: ResetValues) {
    if (!token) {
      toast.error("Missing reset token.");
      return;
    }
    try {
      setSubmitting(true);
      const res = await fetch(`${API_BASE}/auth/password/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token, password: values.password }),
      });

      if (!res.ok) {
        const msg = await safeMessage(res);
        throw new Error(msg || `Reset failed (${res.status})`);
      }

      toast.success("Password updated. You are now logged in.");
      navigate("/"); // or navigate("/login") if you do not auto-login server-side
    } catch (err: any) {
      toast.error(err.message || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Reset password</CardTitle>
          <CardDescription>Enter your new password below.</CardDescription>
        </CardHeader>

        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormItem>
                <FormLabel>Reset token</FormLabel>
                <Input value={token} disabled />
                <p className="text-xs text-muted-foreground mt-1">
                  Token was provided via the link we emailed you.
                </p>
              </FormItem>

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New password</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="••••••••" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirm"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm password</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="••••••••" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Updating…" : "Update password"}
              </Button>

              <div className="text-sm text-center mt-2">
                <Link to="/login" className="underline">Back to login</Link>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}

async function safeMessage(res: Response) {
  try {
    const data = await res.json();
    return (data as any)?.message || (data as any)?.error;
  } catch {
    try {
      return await res.text();
    } catch {
      return "";
    }
  }
}
