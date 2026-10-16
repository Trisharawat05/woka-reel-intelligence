"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Instagram, CheckCircle2, AlertTriangle, Loader2, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function InstagramOAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectedUsername, setConnectedUsername] = useState<string | null>(null);

  useEffect(() => {
    handleOAuthCallback();
  }, []);

  const handleOAuthCallback = async () => {
    const errorParam = searchParams.get("error");
    const errorDesc = searchParams.get("error_description") || searchParams.get("error_reason");
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    // 1. Check if user denied permission or Meta returned an error
    if (errorParam) {
      setStatus("error");
      setErrorMessage(errorDesc || `Meta returned error: ${errorParam}. You may have cancelled the authorization.`);
      return;
    }

    // 2. Validate presence of code and state
    if (!code || !state) {
      setStatus("error");
      setErrorMessage("Missing required authorization code or state parameter from Meta redirect.");
      return;
    }

    // 3. Exchange code via backend API
    try {
      const account = await api.connectInstagram(code, state);
      setStatus("success");
      setConnectedUsername(account.username);
      // Wait a moment then redirect to dashboard
      setTimeout(() => {
        router.push(`/dashboard/instagram?connected=true&username=${encodeURIComponent(account.username)}`);
      }, 1500);
    } catch (err: any) {
      setStatus("error");
      setErrorMessage(err.message || "Failed to exchange authorization code with Meta API. Please try again.");
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-slate-200 shadow-xl">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-gradient-to-tr from-amber-500 via-rose-500 to-violet-600 flex items-center justify-center text-white shadow-md mb-3">
            <Instagram className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold text-slate-900">
            {status === "loading" && "Connecting Instagram Account"}
            {status === "success" && "Connected Successfully!"}
            {status === "error" && "Connection Failed"}
          </CardTitle>
          <CardDescription className="text-xs">
            {status === "loading" && "Verifying Meta credentials and establishing secure connection..."}
            {status === "success" && "Your Instagram professional account is now verified and active."}
            {status === "error" && "We were unable to complete the Instagram connection."}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6 pt-4">
          {status === "loading" && (
            <div className="flex flex-col items-center justify-center py-6 space-y-4">
              <Loader2 className="h-8 w-8 text-violet-600 animate-spin" />
              <div className="text-xs text-slate-500 text-center space-y-1">
                <p className="font-medium text-slate-700">Finalizing OAuth 2.0 handshake</p>
                <p>Exchanging authorization code for long-lived 60-day token...</p>
              </div>
            </div>
          )}

          {status === "success" && (
            <div className="flex flex-col items-center justify-center py-4 space-y-3">
              <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                Connected as <span className="text-violet-600">@{connectedUsername}</span>
              </p>
              <p className="text-xs text-slate-500 text-center">
                Redirecting you back to your workspace dashboard...
              </p>
            </div>
          )}

          {status === "error" && (
            <div className="space-y-4">
              <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-xs text-rose-800 flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-rose-900">Connection Error</p>
                  <p>{errorMessage}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="primary"
                  className="w-full text-xs"
                  onClick={() => router.push("/dashboard/instagram")}
                >
                  <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
                  Return to Instagram Settings
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function InstagramOAuthCallbackPage() {
  return (
    <React.Suspense fallback={
      <div className="min-h-[70vh] flex items-center justify-center p-4">
        <Loader2 className="h-8 w-8 text-violet-600 animate-spin" />
      </div>
    }>
      <InstagramOAuthCallbackContent />
    </React.Suspense>
  );
}
