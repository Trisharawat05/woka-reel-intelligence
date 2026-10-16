"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
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
  Calendar,
  BarChart2,
  Loader2,
  Trash2,
  AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { InstagramAccount, InstagramStatusResponse, InstagramSyncInsightsResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

function InstagramConnectionContent() {
  const searchParams = useSearchParams();

  const [account, setAccount] = useState<InstagramAccount | null>(null);
  const [statusInfo, setStatusInfo] = useState<InstagramStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  const [sandboxEnabled, setSandboxEnabled] = useState(false);
  const [mockHandle, setMockHandle] = useState("alex_creativestudio");
  const [mockFollowers, setMockFollowers] = useState(48500);
  const [copiedWebhook, setCopiedWebhook] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<InstagramSyncInsightsResponse | null>(null);

  useEffect(() => {
    // Check for incoming query params from OAuth redirects
    const connectedParam = searchParams.get("connected");
    const usernameParam = searchParams.get("username");
    const errorParam = searchParams.get("error");
    const errorDescParam = searchParams.get("error_description");

    if (connectedParam === "true") {
      setActionSuccess(
        usernameParam
          ? `Successfully connected Instagram account @${usernameParam} via Meta OAuth 2.0!`
          : "Successfully connected your Instagram account via Meta OAuth 2.0!"
      );
    } else if (errorParam) {
      setActionError(errorDescParam || `Meta authorization failed: ${errorParam}`);
    }

    loadStatusAndAccount();
  }, [searchParams]);

  const loadStatusAndAccount = async () => {
    setLoading(true);
    try {
      const [statusRes, accRes] = await Promise.allSettled([
        api.getInstagramStatus(),
        api.getInstagramAccount()
      ]);

      if (statusRes.status === "fulfilled") {
        setStatusInfo(statusRes.value);
        if (statusRes.value.account) {
          setAccount(statusRes.value.account);
          setSandboxEnabled(statusRes.value.account.is_sandbox && statusRes.value.account.is_connected);
          setMockHandle(statusRes.value.account.username || "alex_creativestudio");
          setMockFollowers(statusRes.value.account.followers_count || 48500);
        }
      }

      if (accRes.status === "fulfilled" && accRes.value) {
        setAccount(accRes.value);
        setSandboxEnabled(accRes.value.is_sandbox && accRes.value.is_connected);
        setMockHandle(accRes.value.username || "alex_creativestudio");
        setMockFollowers(accRes.value.followers_count || 48500);
      }
    } catch (err: any) {
      console.error("Failed to load Instagram connection status:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartMetaOAuth = async () => {
    try {
      const res = await api.getOAuthUrl();
      window.location.href = res.oauth_url;
    } catch (err: any) {
      setActionError(
        err.message ||
        "Could not initiate Meta OAuth. Verify that META_APP_ID is configured in the backend environment."
      );
    }
  };

  const handleSyncInsights = async () => {
    setSyncing(true);
    setActionSuccess(null);
    setActionError(null);
    setSyncResult(null);

    try {
      const res = await api.syncInstagramInsights();
      setSyncResult(res);
      setActionSuccess(
        `Insights synced successfully! Processed ${res.synced_media_count} reels and recorded ${res.metric_snapshots_created} metric snapshots.`
      );
      await loadStatusAndAccount();
    } catch (err: any) {
      setActionError(err.message || "Failed to synchronize Instagram Insights from Meta API.");
    } finally {
      setSyncing(false);
    }
  };

  const handleRefreshToken = async () => {
    setRefreshing(true);
    setActionSuccess(null);
    setActionError(null);

    try {
      const res = await api.refreshInstagramToken();
      setActionSuccess(res.message || "Access token successfully refreshed for an additional 60 days.");
      await loadStatusAndAccount();
    } catch (err: any) {
      setActionError(err.message || "Failed to refresh long-lived access token with Meta.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleDisconnect = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to disconnect this Instagram account? Stored access tokens will be securely wiped and insights synchronization will cease."
    );
    if (!confirmed) return;

    setDisconnecting(true);
    setActionSuccess(null);
    setActionError(null);

    try {
      if (account?.is_sandbox) {
        await api.toggleSandbox(false);
      } else {
        await api.disconnectInstagram();
      }
      setAccount(null);
      setStatusInfo(null);
      setSandboxEnabled(false);
      setSyncResult(null);
      setActionSuccess("Instagram account has been successfully disconnected.");
      await loadStatusAndAccount();
    } catch (err: any) {
      setActionError(err.message || "Failed to disconnect account.");
    } finally {
      setDisconnecting(false);
    }
  };

  const handleToggleSandbox = async (enabled: boolean) => {
    setLoading(true);
    setActionSuccess(null);
    setActionError(null);

    try {
      const acc = await api.toggleSandbox(enabled, mockHandle, mockFollowers);
      setAccount(acc);
      setSandboxEnabled(acc.is_connected && acc.is_sandbox);
      setActionSuccess(
        enabled
          ? "Interactive Demo Sandbox activated! You can now analyze sample reels and test automations."
          : "Demo Sandbox disabled."
      );
      await loadStatusAndAccount();
    } catch (err: any) {
      setActionError(err.message || "Failed to update sandbox mode.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: "webhook" | "token") => {
    navigator.clipboard.writeText(text);
    if (type === "webhook") {
      setCopiedWebhook(true);
      setTimeout(() => setCopiedWebhook(false), 2000);
    } else {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    }
  };

  const isConnected = account?.is_connected === true && statusInfo?.is_connected !== false;
  const tokenExpiresAt = account?.token_expires_at ? new Date(account.token_expires_at) : null;
  const isTokenExpired = account?.is_token_expired || (tokenExpiresAt ? tokenExpiresAt.getTime() < Date.now() : false);

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Meta Instagram Account Connection
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Connect your Instagram Professional (Creator or Business) account via the official Meta Graph API v21.0 / v22.0.
        </p>
      </div>

      {/* Alert Banners */}
      {actionSuccess && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-xs font-semibold text-emerald-800 flex items-center justify-between gap-2 shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-600 hover:text-emerald-900 text-xs underline font-normal"
          >
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-xs font-semibold text-rose-800 flex items-center justify-between gap-2 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-rose-600 hover:text-rose-900 text-xs underline font-normal"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Connected Account Overview */}
      {isConnected && account ? (
        <div className="space-y-6">
          <Card className="border-violet-200 bg-white shadow-md">
            <CardContent className="p-6">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div className="flex items-start sm:items-center gap-4">
                  <div className="relative flex-shrink-0">
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
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-bold text-slate-900">@{account.username}</h3>
                      {account.is_sandbox ? (
                        <Badge variant="sandbox">Sandbox Demo Account</Badge>
                      ) : (
                        <Badge variant="success">Official Meta Sync</Badge>
                      )}
                      {isTokenExpired ? (
                        <Badge variant="danger">Token Expired</Badge>
                      ) : (
                        <Badge variant="success">Active Token (60-Day)</Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{account.name || "Professional Creator Profile"}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-600 font-medium">
                      <span><strong>{account.followers_count?.toLocaleString() || 0}</strong> Followers</span>
                      <span>•</span>
                      <span><strong>{account.media_count || 0}</strong> Media Posts</span>
                      <span>•</span>
                      <span className="text-emerald-600 flex items-center gap-1">
                        <Lock className="h-3 w-3" /> Token Encrypted (AES-256-GCM)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Status Badges & Disconnect */}
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleDisconnect}
                    isLoading={disconnecting}
                    className="text-xs text-rose-600 hover:bg-rose-50 hover:border-rose-200"
                  >
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                    Disconnect Account
                  </Button>
                </div>
              </div>

              {/* Token & Insights Health Diagnostics */}
              <div className="mt-6 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="text-slate-500 flex items-center gap-1.5 font-medium">
                    <Calendar className="h-3.5 w-3.5 text-slate-400" />
                    Token Expiration
                  </div>
                  <div className="font-semibold text-slate-800">
                    {tokenExpiresAt ? tokenExpiresAt.toLocaleDateString(undefined, { dateStyle: "medium" }) : "N/A (Managed)"}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {isTokenExpired ? "Requires reauthorization" : "Valid 60-day Meta token"}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="text-slate-500 flex items-center gap-1.5 font-medium">
                    <ShieldCheck className="h-3.5 w-3.5 text-violet-500" />
                    Insights Permission
                  </div>
                  <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                    {statusInfo?.has_insights_permission !== false ? (
                      <span className="text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Granted
                      </span>
                    ) : (
                      <span className="text-amber-700 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5 text-amber-500" /> Missing Scope
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    <code>instagram_business_manage_insights</code>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="text-slate-500 flex items-center gap-1.5 font-medium">
                    <BarChart2 className="h-3.5 w-3.5 text-blue-500" />
                    Graph API Target
                  </div>
                  <div className="font-semibold text-slate-800">
                    {statusInfo?.api_version || "v21.0 / v22.0"}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Reel Metrics: views, reach, saves, shares
                  </div>
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSyncInsights}
                  isLoading={syncing}
                  className="text-xs bg-violet-600 hover:bg-violet-700"
                >
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncing ? "animate-spin" : ""}`} />
                  Sync Insights Now
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleRefreshToken}
                  isLoading={refreshing}
                  className="text-xs"
                >
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? "animate-spin" : ""}`} />
                  Refresh 60-Day Token
                </Button>
              </div>

              {/* Sync Result Details */}
              {syncResult && (
                <div className="mt-4 p-4 rounded-xl bg-violet-50 border border-violet-100 text-xs text-violet-900 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-violet-600" />
                    Last Sync Execution ({syncResult.status})
                  </div>
                  <p>
                    Target: <code>{syncResult.provenance?.source_endpoint}</code> ({syncResult.provenance?.mode})
                  </p>
                  <p>
                    Created {syncResult.metric_snapshots_created} verified snapshots across {syncResult.synced_media_count} reels.
                  </p>
                  {syncResult.errors && syncResult.errors.length > 0 && (
                    <div className="mt-2 text-rose-700 space-y-1">
                      <p className="font-semibold">Non-fatal sync notes:</p>
                      {syncResult.errors.map((e, idx) => (
                        <p key={idx} className="font-mono text-[11px]">• {e}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
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
                  <span><code>instagram_business_basic</code> — Read profile & published media</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span><code>instagram_business_manage_insights</code> — Access Reel metrics & views</span>
                </div>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 text-[11px] text-slate-600">
                <p>
                  Redirects securely to Meta&apos;s OAuth consent dialog with HMAC-SHA256 state validation. Tokens are stored encrypted with AES-256-GCM.
                </p>
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
                Instant 1-click test mode. Perfect for exploring Reel Intelligence without waiting for Meta App Review approval.
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
                Enter these endpoints in your Meta App Dashboard under Messenger &gt; Webhooks or Instagram Webhooks.
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
                <button
                  type="button"
                  onClick={() => copyToClipboard("http://localhost:8000/api/v1/instagram/webhook", "webhook")}
                  aria-label="Copy Webhook Callback URL"
                >
                  {copiedWebhook ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-slate-700 block">Verify Token</span>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-slate-800 text-[11px]">
                <span className="truncate flex-1">woka_meta_webhook_verify_token_2026</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard("woka_meta_webhook_verify_token_2026", "token")}
                  aria-label="Copy Verify Token"
                >
                  {copiedToken ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />}
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

export default function InstagramConnectionPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 text-violet-600 animate-spin" />
      </div>
    }>
      <InstagramConnectionContent />
    </Suspense>
  );
}
