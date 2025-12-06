// src/pages/ForgotPassword.tsx
import * as React from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";

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

const ForgotSchema = z.object({
  email: z.string().email("Enter a valid email"),
});
type ForgotValues = z.infer<typeof ForgotSchema>;

// Set in frontend/.env: VITE_API_URL=http://localhost:5000
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function ForgotPassword() {
  const [submitting, setSubmitting] = React.useState(false);

  const form = useForm<ForgotValues>({
    resolver: zodResolver(ForgotSchema),
    defaultValues: { email: "" },
    mode: "onSubmit",
  });

  async function onSubmit(values: ForgotValues) {
    try {
      setSubmitting(true);

      const res = await fetch(`${API_BASE}/auth/password/forgot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(values), // { email }
      });

      // For security, your backend always returns 200-like messaging; we still handle non-OK safely.
      if (!res.ok) {
        const msg = await safeMessage(res);
        // Keep success-style UX to avoid account enumeration, but show dev-friendly toast
        toast.error(msg || `Request failed (${res.status})`);
      }

      toast.success("If the email is registered, a reset link has been sent.");
      form.reset();
    } catch (err: any) {
      toast.error(err?.message || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Forgot password</CardTitle>
          <CardDescription>Enter your email and we’ll send a reset link.</CardDescription>
        </CardHeader>

        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="you@example.com"
                        autoComplete="email"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Sending…" : "Send reset link"}
              </Button>

              <div className="text-center text-sm mt-2">
                <Link to="/login" className="underline">Back to login</Link>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}

// helper to read backend error text safely
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
