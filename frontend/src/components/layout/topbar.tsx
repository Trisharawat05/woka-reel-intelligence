"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bell,
  CheckCircle2,
  LogOut,
  Sparkles,
  Instagram,
  Menu,
  X,
  ExternalLink
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { NotificationItem, InstagramAccount } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface TopbarProps {
  onToggleMobileMenu?: () => void;
}

export function Topbar({ onToggleMobileMenu }: TopbarProps) {
  const router = useRouter();
  const { user, workspace, logout } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [account, setAccount] = useState<InstagramAccount | null>(null);

  useEffect(() => {
    if (user) {
      api.listNotifications().then(setNotifications).catch(() => {});
      api.getInstagramAccount().then(setAccount).catch(() => {});
    }
  }, [user]);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {}
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 sm:px-8 backdrop-blur-md">
      {/* Left: Mobile hamburger & Workspace name */}
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-700">
            {workspace?.name ? workspace.name.charAt(0).toUpperCase() : "W"}
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="text-sm font-semibold text-slate-900 leading-tight">
              {workspace?.name || "My Workspace"}
            </span>
            <span className="text-[11px] text-slate-500">
              {user?.role === "BRAND" ? "Brand Partner" : "Creator Pro Account"}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Meta Status, Notifications, User Menu */}
      <div className="flex items-center gap-2.5 sm:gap-4">
        {/* Instagram Account Connection Pill */}
        {account?.is_connected ? (
          <div className="flex items-center gap-1.5 rounded-full bg-slate-50 border border-slate-200 px-2.5 py-1 text-xs">
            <Instagram className="h-3.5 w-3.5 text-rose-500" />
            <span className="font-semibold text-slate-700 hidden md:inline">@{account.username}</span>
            {account.is_sandbox ? (
              <Badge variant="sandbox" className="text-[10px] py-0 px-1.5">
                Sandbox Demo
              </Badge>
            ) : (
              <Badge variant="success" className="text-[10px] py-0 px-1.5">
                Live Meta Sync
              </Badge>
            )}
          </div>
        ) : (
          <Link href="/dashboard/instagram">
            <Button variant="secondary" size="sm" className="h-8 text-xs">
              <Instagram className="h-3.5 w-3.5 text-rose-500 mr-1.5" />
              Connect IG
            </Button>
          </Link>
        )}

        {/* Notifications Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100 transition-colors"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl z-50 animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-2">
                <span className="font-semibold text-sm text-slate-900">Notifications</span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-xs text-violet-600 hover:underline font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto space-y-2">
                {notifications.length === 0 ? (
                  <p className="text-center text-xs text-slate-400 py-6">No new notifications</p>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-2.5 rounded-xl border text-xs transition-colors ${
                        n.is_read ? "border-transparent bg-slate-50/50" : "border-violet-100 bg-violet-50/40"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-900">{n.title}</span>
                        <span className="text-[10px] text-slate-400">
                          {new Date(n.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-slate-600 mt-1">{n.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Info & Logout */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-100 text-violet-700 font-bold text-xs">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
          </div>
          <button
            onClick={handleLogout}
            title="Log out"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
