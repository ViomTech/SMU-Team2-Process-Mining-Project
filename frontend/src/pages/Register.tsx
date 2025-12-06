// src/pages/Register.tsx
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

// ✅ Add role to schema (BPO/Admin only)
const RegisterSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(3, "At least 3 characters"),
  confirmPassword: z.string().min(3, "At least 3 characters"),
  role: z.enum(["BPO", "Admin"], { required_error: "Select a role" }),
}).refine((vals) => vals.password === vals.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type RegisterValues = z.infer<typeof RegisterSchema>;
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function Register() {
  const [submitting, setSubmitting] = React.useState(false);
  const navigate = useNavigate();

  const form = useForm<RegisterValues>({
    resolver: zodResolver(RegisterSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "", role: "BPO" },
    mode: "onSubmit",
  });

  async function onSubmit(values: RegisterValues) {
    try {
      setSubmitting(true);
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: values.name,
          email: values.email,
          password: values.password,
          role: values.role, // ✅ send role
        }),
      });

      if (!res.ok) {
        const msg = await safeMessage(res);
        throw new Error(msg || `Registration failed (${res.status})`);
      }

      toast.success("Account created! You’re logged in.");
      navigate("/");
    } catch (err: any) {
      toast.error(`Registration failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create account</CardTitle>
          <CardDescription>Sign up with your name, email and password.</CardDescription>
        </CardHeader>

        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Jane Doe" autoComplete="name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
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
                      <Input type="password" placeholder="•••" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm password</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="•••" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ✅ Role selection */}
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role</FormLabel>
                    <FormControl>
                      <div className="flex gap-4">
                        <label className="flex items-center gap-2 text-sm select-none">
                          <input
                            type="radio"
                            value="BPO"
                            checked={field.value === "BPO"}
                            onChange={() => field.onChange("BPO")}
                          />
                          BPO
                        </label>
                        <label className="flex items-center gap-2 text-sm select-none">
                          <input
                            type="radio"
                            value="Admin"
                            checked={field.value === "Admin"}
                            onChange={() => field.onChange("Admin")}
                          />
                          Admin
                        </label>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Creating account…" : "Create account"}
              </Button>

              <div className="text-sm text-center">
                Already have an account?{" "}
                <Link to="/login" className="underline">Log in</Link>
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
