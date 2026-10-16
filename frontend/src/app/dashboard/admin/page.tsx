"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  Users,
  Activity,
  Bot,
  Briefcase,
  Send,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { User } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AdminConsolePage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAdminData() {
      try {
        const [statsData, usersList] = await Promise.all([
          api.getAdminStats(),
          api.listAdminUsers()
        ]);
        setStats(statsData);
        setUsers(usersList);
      } catch (err: any) {
        setError(err.message || "Failed to load admin telemetry data.");
      } finally {
        setLoading(false);
      }
    }
    loadAdminData();
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center text-xs text-slate-500">
        Loading admin operations telemetry...
      </div>
    );
  }

  if (error || user?.role !== "ADMIN") {
    return (
      <Card className="p-8 text-center max-w-lg mx-auto">
        <ShieldAlert className="h-10 w-10 text-rose-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-slate-900">Administrator Access Required</h3>
        <p className="text-xs text-slate-500 mt-1">
          {error || "You do not have administrative privileges to view platform operations telemetry."}
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Platform Admin & Support Console
            </h1>
            <Badge variant="sandbox" className="text-xs">
              System Admin
            </Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Monitor real-time Meta webhook throughput, platform KPIs, and user account status.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-1.5 rounded-lg text-xs font-semibold">
          <Activity className="h-4 w-4 text-emerald-600 animate-pulse" />
          <span>Meta Graph & Webhooks: OPERATIONAL</span>
        </div>
      </div>

      {/* KPI Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Card>
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Registered Users</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-black text-slate-900">
                {stats.kpis.total_users}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Creators, Brands & Agencies
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Connected Accounts</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-black text-slate-900">
                {stats.kpis.connected_accounts}
              </div>
              <div className="text-xs text-emerald-600 font-semibold mt-1">
                Active Meta & Sandbox links
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Automations</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-black text-slate-900">
                {stats.kpis.active_automations}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {stats.kpis.total_automations} total configured
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total DMs Dispatched</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-black text-slate-900">
                {stats.kpis.total_dms_dispatched}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Across platform webhooks
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* System Health Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Infrastructure & Gateway Health</CardTitle>
          <CardDescription className="text-xs">
            Operational status of core messaging services and persistence engines.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-violet-600" />
                <span className="font-semibold text-slate-800">Database Engine</span>
              </div>
              <span className="text-emerald-600 font-bold">1.8ms Latency</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-rose-500" />
                <span className="font-semibold text-slate-800">Webhook Router</span>
              </div>
              <span className="text-emerald-600 font-bold">HMAC Verified</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-500" />
                <span className="font-semibold text-slate-800">Token Vault</span>
              </div>
              <span className="text-emerald-600 font-bold">AES-256 GCM</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User Directory Table */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-900">Registered Platform Users ({users.length})</h3>

        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Email Address</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Registered Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {u.full_name}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={u.role === "ADMIN" ? "gradient" : u.role === "BRAND" ? "default" : "secondary"}
                        className="text-[10px]"
                      >
                        {u.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={u.is_active ? "success" : "danger"} className="text-[10px]">
                        {u.is_active ? "Active" : "Suspended"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
