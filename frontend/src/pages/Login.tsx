// src/pages/Login.tsx
import * as React from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, Link } from "react-router-dom";

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

// ✅ Make `remember` a required boolean to avoid boolean | undefined mismatches
const LoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(3, "At least 3 characters"),
  remember: z.boolean(),
});

type LoginValues = z.infer<typeof LoginSchema>;

// Optional: put your API base in .env as VITE_API_URL=http://localhost:5000
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function Login() {
  const [submitting, setSubmitting] = React.useState(false);
  const navigate = useNavigate();

  // ✅ Use the same inferred type + provide concrete default for remember
  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: "", password: "", remember: false },
    mode: "onSubmit",
  });

  async function onSubmit(values: LoginValues) {
    try {
      setSubmitting(true);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // needed if backend sets httpOnly cookie
        body: JSON.stringify(values), // includes { email, password, remember }
      });

      if (!res.ok) {
        const msg = await safeMessage(res);
        throw new Error(msg || `Login failed (${res.status})`);
      }

      toast.success("Welcome back! You’ve logged in successfully.");
      navigate("/"); // change to dashboard route if needed
    } catch (err: any) {
      toast.error(`Login failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Log in</CardTitle>
          <CardDescription>Enter your email and password to continue.</CardDescription>
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

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="•••"
                        autoComplete="current-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Remember me + Forgot password */}
              <div className="flex items-center justify-between">
                <FormField
                  control={form.control}
                  name="remember"
                  render={({ field }) => (
                    <label className="flex items-center gap-2 text-sm select-none">
                      {/* ✅ Ensure this is a controlled boolean value */}
                      <input
                        type="checkbox"
                        checked={!!field.value}
                        onChange={(e) => field.onChange(e.target.checked)}
                      />
                      Remember me
                    </label>
                  )}
                />
                <Link to="/forgot-password" className="text-sm underline">
                  Forgot password?
                </Link>
              </div>

              
              <div className="text-sm text-center mt-2">
                New here? <Link to="/register" className="underline">Create an account</Link>
              </div>

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
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
