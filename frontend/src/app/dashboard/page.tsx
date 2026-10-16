"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  Users,
  Send,
  Sparkles,
  TrendingUp,
  Share2,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowRight,
  Instagram,
  Eye,
  Plus
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { InstagramAccount, Automation, AutomationLog, AnalyticsResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/utils";

export default function DashboardOverviewPage() {
  const { user, workspace } = useAuth();
  const [account, setAccount] = useState<InstagramAccount | null>(null);
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [logs, setLogs] = useState<AutomationLog[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const [acc, autos, logList, ana] = await Promise.all([
          api.getInstagramAccount().catch(() => null),
          api.listAutomations().catch(() => []),
          api.getAutomationLogs().catch(() => []),
          api.getAnalytics().catch(() => null)
        ]);
        setAccount(acc);
        setAutomations(autos);
        setLogs(logList.slice(0, 5));
        setAnalytics(ana);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const totalDMsSent = automations.reduce((acc, a) => acc + a.total_triggered_count, 0);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Welcome back, {user?.full_name?.split(" ")[0] || "Creator"} 👋
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Here is what&apos;s happening across your automations, reach, and brand partnerships today.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/dashboard/automations">
            <Button variant="secondary" size="sm">
              <Play className="h-3.5 w-3.5 mr-1.5 text-violet-600" />
              Test Simulator
            </Button>
          </Link>
          <Link href="/dashboard/automations">
            <Button variant="gradient" size="sm">
              <Plus className="h-4 w-4 mr-1.5" />
              New Automation
            </Button>
          </Link>
        </div>
      </div>

      {/* Account Connection Status Notice */}
      {!account?.is_connected && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
              <AlertCircle className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-amber-900">Instagram Account Not Linked</h4>
              <p className="text-xs text-amber-700 mt-0.5">
                Connect your professional Instagram account or toggle Demo Sandbox mode to start automating comment DMs.
              </p>
            </div>
          </div>
          <Link href="/dashboard/instagram">
            <Button variant="primary" size="sm" className="bg-amber-600 hover:bg-amber-700 text-white">
              Configure Connection &rarr;
            </Button>
          </Link>
        </div>
      )}

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1 */}
        <Card className="hover:border-violet-300">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Followers
            </span>
            <div className="h-8 w-8 rounded-lg bg-violet-100 flex items-center justify-center text-violet-600">
              <Users className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(account?.followers_count || 48500)}
            </div>
            <div className="mt-1 flex items-center text-xs text-emerald-600 font-semibold gap-1">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>+960 this month (4.2% growth)</span>
            </div>
          </CardContent>
        </Card>

        {/* Metric 2 */}
        <Card className="hover:border-violet-300">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Automated DMs Dispatched
            </span>
            <div className="h-8 w-8 rounded-lg bg-rose-100 flex items-center justify-center text-rose-600">
              <Send className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(totalDMsSent || 142)}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Across <span className="font-semibold text-slate-700">{automations.length} active rules</span>
            </div>
          </CardContent>
        </Card>

        {/* Metric 3 */}
        <Card className="hover:border-violet-300">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Avg. Engagement Rate
            </span>
            <div className="h-8 w-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-600">
              <TrendingUp className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {analytics?.summary.avg_engagement_rate ? `${analytics.summary.avg_engagement_rate}%` : "4.25%"}
            </div>
            <div className="mt-1 text-xs text-emerald-600 font-semibold flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Higher than 82% of creator peers</span>
            </div>
          </CardContent>
        </Card>

        {/* Metric 4 */}
        <Card className="hover:border-violet-300">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              30-Day Reach
            </span>
            <div className="h-8 w-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
              <Eye className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(analytics?.summary.reach_30d || 164900)}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              3.4x Audience Multiplier
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid: Active Automations + Execution Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Active Automations List (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">Active Comment Automations</h3>
              <p className="text-xs text-slate-500">Live rules responding to fan keywords</p>
            </div>
            <Link href="/dashboard/automations" className="text-xs font-semibold text-violet-600 hover:underline">
              View All &rarr;
            </Link>
          </div>

          <div className="space-y-3">
            {automations.length === 0 ? (
              <Card className="p-8 text-center text-slate-500 text-sm">
                <Bot className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                <p>No automations set up yet.</p>
                <Link href="/dashboard/automations">
                  <Button variant="gradient" size="sm" className="mt-4">
                    Create Your First Rule
                  </Button>
                </Link>
              </Card>
            ) : (
              automations.map((auto) => (
                <Card key={auto.id} className="p-4 hover:border-violet-200">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-900">{auto.name}</span>
                        {auto.is_active ? (
                          <Badge variant="success" className="text-[10px] py-0 px-1.5">Active</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px] py-0 px-1.5">Paused</Badge>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 flex flex-wrap items-center gap-2">
                        <span>Keywords:</span>
                        {auto.trigger_keywords.map((kw) => (
                          <span key={kw} className="bg-slate-100 rounded px-1.5 py-0.5 text-slate-700 font-mono text-[11px]">
                            #{kw}
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-slate-600 truncate max-w-md italic mt-1">
                        DM: &quot;{auto.dm_message_template}&quot;
                      </p>
                    </div>

                    <div className="flex items-center gap-4 text-xs sm:border-l sm:border-slate-100 sm:pl-4">
                      <div className="text-center">
                        <span className="block font-bold text-slate-900 text-sm">{auto.total_triggered_count}</span>
                        <span className="text-[10px] text-slate-600">Dispatched</span>
                      </div>
                      <Link href="/dashboard/automations">
                        <Button variant="secondary" size="sm">
                          Edit
                        </Button>
                      </Link>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Recent Execution Logs (1 Col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">Recent Activity</h3>
              <p className="text-xs text-slate-500">Live webhook trigger stream</p>
            </div>
            <Link href="/dashboard/automations" className="text-xs font-semibold text-violet-600 hover:underline">
              Logs
            </Link>
          </div>

          <Card>
            <CardContent className="p-4 divide-y divide-slate-100">
              {logs.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No execution logs recorded yet. Run a test comment in the simulator!
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="py-3 first:pt-0 last:pb-0 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-900">@{log.recipient_username}</span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600">
                      Commented: <span className="italic text-slate-700">&quot;{log.trigger_comment_text}&quot;</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>{log.status === "SIMULATED" ? "Simulated DM Sent" : "Delivered to Instagram DM"}</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
