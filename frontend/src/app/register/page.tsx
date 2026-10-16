"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { User, Briefcase, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"CREATOR" | "BRAND" | "AGENCY">("CREATOR");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register({
        full_name: fullName,
        email,
        password,
        role,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please check your details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link href="/" className="inline-flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-woka text-white font-bold text-xl shadow-md shadow-violet-500/20">
            W
          </div>
          <span className="font-extrabold text-2xl tracking-tight text-slate-900">Woka</span>
        </Link>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
          Create your Woka workspace
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-violet-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <Card className="shadow-lg border-slate-200">
          <CardHeader>
            <CardTitle className="text-base">Select Your Primary Role</CardTitle>
            <CardDescription className="text-xs">
              Tailor your Woka workspace tools for your workflow:
            </CardDescription>

            <div className="grid grid-cols-3 gap-2 mt-3">
              <button
                type="button"
                onClick={() => setRole("CREATOR")}
                className={cn(
                  "flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-semibold transition-all",
                  role === "CREATOR"
                    ? "border-violet-500 bg-violet-50/60 text-violet-700 shadow-sm"
                    : "border-slate-200 hover:bg-slate-50 text-slate-600"
                )}
              >
                <User className="h-4 w-4 mb-1 text-violet-600" />
                <span>Creator</span>
              </button>

              <button
                type="button"
                onClick={() => setRole("BRAND")}
                className={cn(
                  "flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-semibold transition-all",
                  role === "BRAND"
                    ? "border-rose-500 bg-rose-50/60 text-rose-700 shadow-sm"
                    : "border-slate-200 hover:bg-slate-50 text-slate-600"
                )}
              >
                <Briefcase className="h-4 w-4 mb-1 text-rose-500" />
                <span>Brand</span>
              </button>

              <button
                type="button"
                onClick={() => setRole("AGENCY")}
                className={cn(
                  "flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-semibold transition-all",
                  role === "AGENCY"
                    ? "border-amber-500 bg-amber-50/60 text-amber-800 shadow-sm"
                    : "border-slate-200 hover:bg-slate-50 text-slate-600"
                )}
              >
                <Building2 className="h-4 w-4 mb-1 text-amber-600" />
                <span>Agency</span>
              </button>
            </div>
          </CardHeader>

          <CardContent className="pt-2">
            {error && (
              <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Full Name or Brand Name"
                placeholder="Alex Rivera"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />

              <Input
                label="Email Address"
                type="email"
                placeholder="alex@creativestudio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Input
                label="Password"
                type="password"
                placeholder="At least 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />

              <Button type="submit" variant="gradient" className="w-full h-10 mt-2" isLoading={loading}>
                Create Account &rarr;
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
