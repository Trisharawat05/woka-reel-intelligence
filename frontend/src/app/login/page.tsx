"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, User, Briefcase, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setLoading(true);
    try {
      await login(demoEmail, demoPass);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
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
          Sign in to your creator workspace
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-semibold text-violet-600 hover:underline">
            Register free
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <Card className="shadow-lg border-slate-200">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Quick Demo Access</CardTitle>
              <Badge variant="sandbox" className="text-[10px]">
                1-Click Sign In
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Explore Woka immediately with pre-configured verified creator, brand, or admin accounts:
            </CardDescription>

            <div className="grid grid-cols-3 gap-2 mt-3">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleQuickLogin("creator@woka.io", "Creator123!")}
                className="flex flex-col h-auto py-2 px-1 text-center"
              >
                <User className="h-4 w-4 text-violet-600 mb-1" />
                <span className="text-xs font-semibold">Creator</span>
                <span className="text-[10px] text-slate-600 font-normal">Alex (48k)</span>
              </Button>

              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleQuickLogin("brand@luminaudio.com", "Brand123!")}
                className="flex flex-col h-auto py-2 px-1 text-center"
              >
                <Briefcase className="h-4 w-4 text-rose-500 mb-1" />
                <span className="text-xs font-semibold">Brand</span>
                <span className="text-[10px] text-slate-600 font-normal">Lumin Tech</span>
              </Button>

              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleQuickLogin("admin@woka.io", "Admin123!")}
                className="flex flex-col h-auto py-2 px-1 text-center"
              >
                <ShieldCheck className="h-4 w-4 text-emerald-600 mb-1" />
                <span className="text-xs font-semibold">Admin</span>
                <span className="text-[10px] text-slate-600 font-normal">Ops Hub</span>
              </Button>
            </div>
          </CardHeader>

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-slate-600 font-semibold">Or with email</span>
            </div>
          </div>

          <CardContent className="pt-4">
            {error && (
              <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Email Address"
                type="email"
                placeholder="you@creator.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <Button type="submit" variant="gradient" className="w-full h-10 mt-2" isLoading={loading}>
                Sign In
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
