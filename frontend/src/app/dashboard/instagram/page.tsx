"use client";

import React, { useState, useEffect } from "react";
import {
  Instagram,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  Lock,
  Layers,
  Key
} from "lucide-react";
import { api } from "@/lib/api";
import { InstagramAccount } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export default function InstagramConnectionPage() {
  const [account, setAccount] = useState<InstagramAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [sandboxEnabled, setSandboxEnabled] = useState(false);
  const [mockHandle, setMockHandle] = useState("alex_creativestudio");
  const [mockFollowers, setMockFollowers] = useState(48500);
  const [copiedWebhook, setCopiedWebhook] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadAccount();
  }, []);

  const loadAccount = async () => {
    try {
      const acc = await api.getInstagramAccount();
      setAccount(acc);
      if (acc) {
        setSandboxEnabled(acc.is_sandbox && acc.is_connected);
        setMockHandle(acc.username);
        setMockFollowers(acc.followers_count);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSandbox = async (enabled: boolean) => {
    setLoading(true);
    try {
      const acc = await api.toggleSandbox(enabled, mockHandle, mockFollowers);
      setAccount(acc);
      setSandboxEnabled(acc.is_connected && acc.is_sandbox);
      setActionSuccess(
        enabled
          ? "Interactive Demo Sandbox activated! You can now test automations and explore analytics."
          : "Demo Sandbox disabled."
      );
      setTimeout(() => setActionSuccess(null), 4000);
    } finally {
      setLoading(false);
    }
  };

  const handleStartMetaOAuth = async () => {
    try {
      const res = await api.getOAuthUrl();
      // Redirect to Meta OAuth consent screen
      window.location.href = res.oauth_url;
    } catch {
      alert("Note: To connect a live Meta account, configure META_APP_ID in backend .env. Use Sandbox Demo Mode for instant testing.");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedWebhook(true);
    setTimeout(() => setCopiedWebhook(false), 2000);
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Meta Instagram Account Connection
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Connect your Instagram Professional (Creator or Business) account via the official Meta Graph API.
        </p>
      </div>

      {actionSuccess && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Connected Account Overview */}
      {account?.is_connected ? (
        <Card className="border-violet-200 bg-white shadow-md">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="relative">
                  {/* Avatar */}
                  <img
                    src={account.profile_pic_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120"}
                    alt={account.username}
                    className="h-16 w-16 rounded-full border-2 border-violet-500 object-cover shadow-sm"
                  />
                  <div className="absolute -bottom-1 -right-1 rounded-full bg-rose-500 p-1 text-white shadow-sm">
                    <Instagram className="h-3.5 w-3.5" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-slate-900">@{account.username}</h3>
                    {account.is_sandbox ? (
                      <Badge variant="sandbox">Sandbox Demo Account</Badge>
                    ) : (
                      <Badge variant="success">Official Meta Sync</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{account.name || "Creator Profile"}</p>
                  <div className="mt-2 flex items-center gap-4 text-xs text-slate-600 font-medium">
                    <span><strong>{account.followers_count.toLocaleString()}</strong> Followers</span>
                    <span>•</span>
                    <span><strong>{account.media_count}</strong> Posts</span>
                    <span>•</span>
                    <span className="text-emerald-600 flex items-center gap-1">
                      <Lock className="h-3 w-3" /> Token Encrypted (AES-256)
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleToggleSandbox(false)}
                  className="text-xs text-rose-600 hover:bg-rose-50 hover:border-rose-200"
                >
                  Disconnect
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Option A: Official Meta Live OAuth */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-violet-100 flex items-center justify-center text-violet-600 mb-2">
                <Instagram className="h-5 w-5" />
              </div>
              <CardTitle>Official Meta Instagram Login</CardTitle>
              <CardDescription>
                Connect using your Facebook Login associated with your Instagram Creator or Business page.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs text-slate-600">
              <div className="space-y-2">
                <div className="font-semibold text-slate-800">Required Permissions:</div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span><code>instagram_manage_comments</code> — Listen to comment keywords</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span><code>instagram_manage_messages</code> — Dispatch outbound direct messages</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span><code>pages_show_list</code> — Link verified business Facebook page</span>
                </div>
              </div>

              <Button variant="gradient" className="w-full mt-4" onClick={handleStartMetaOAuth}>
                <Instagram className="h-4 w-4 mr-2" />
                <span>Connect via Meta OAuth</span>
              </Button>
            </CardContent>
          </Card>

          {/* Option B: Interactive Demo Sandbox */}
          <Card className="border-amber-200 bg-amber-50/40">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700 mb-2">
                <Layers className="h-5 w-5" />
              </div>
              <CardTitle>Interactive Demo Sandbox</CardTitle>
              <CardDescription>
                Instant 1-click test mode. Perfect for exploring automations without waiting for Meta App Review approval.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs text-slate-600">
              <div className="space-y-2">
                <Input
                  label="Mock Instagram Handle"
                  value={mockHandle}
                  onChange={(e) => setMockHandle(e.target.value)}
                />
                <Input
                  label="Mock Followers Count"
                  type="number"
                  value={mockFollowers}
                  onChange={(e) => setMockFollowers(Number(e.target.value))}
                />
              </div>

              <Button
                variant="primary"
                className="w-full bg-amber-600 hover:bg-amber-700 text-white"
                onClick={() => handleToggleSandbox(true)}
                isLoading={loading}
              >
                <span>Enable Demo Sandbox Account &rarr;</span>
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Official Webhook Configuration Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Official Meta Webhook Configuration</CardTitle>
              <CardDescription className="text-xs">
                Enter these endpoints in your Meta App Dashboard under Messenger &gt; Webhooks.
              </CardDescription>
            </div>
            <Badge variant="success" className="text-xs">
              Handshake Active
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="font-semibold text-slate-700 block">Callback URL</span>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-slate-800 text-[11px]">
                <span className="truncate flex-1">http://localhost:8000/api/v1/instagram/webhook</span>
                <button onClick={() => copyToClipboard("http://localhost:8000/api/v1/instagram/webhook")}>
                  {copiedWebhook ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-slate-700 block">Verify Token</span>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-slate-800 text-[11px]">
                <span className="truncate flex-1">woka_meta_webhook_verify_token_2026</span>
                <button onClick={() => copyToClipboard("woka_meta_webhook_verify_token_2026")}>
                  {copiedWebhook ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />}
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs text-slate-600 space-y-1">
            <span className="font-semibold text-slate-800">Security & Verification:</span>
            <p>
              Inbound Meta webhook events are verified using <code>X-Hub-Signature-256</code> HMAC signatures matching your server secret. Duplicate delivery attempts are prevented via idempotent event tracking.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
