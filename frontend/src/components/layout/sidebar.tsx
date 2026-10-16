"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Instagram,
  Bot,
  BarChart3,
  Sparkles,
  Share2,
  Briefcase,
  Receipt,
  CreditCard,
  ShieldAlert,
  Zap,
  ExternalLink
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";

const navigationItems = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Instagram Sync", href: "/dashboard/instagram", icon: Instagram },
  { name: "Automations", href: "/dashboard/automations", icon: Bot, badge: "Core" },
  { name: "Analytics & Reach", href: "/dashboard/analytics", icon: BarChart3 },
  { name: "AI Content Studio", href: "/dashboard/ai-studio", icon: Sparkles },
  { name: "Media Kit & Rates", href: "/dashboard/media-kit", icon: Share2 },
  { name: "Brand Marketplace", href: "/dashboard/campaigns", icon: Briefcase },
  { name: "Invoices & Rates", href: "/dashboard/invoices", icon: Receipt },
  { name: "Plan & Usage", href: "/dashboard/billing", icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
      {/* Brand Logo Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-100 px-6">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-woka shadow-md shadow-violet-500/20 text-white font-bold text-lg tracking-tight">
            W
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-slate-900 tracking-tight text-xl leading-none">
              Woka
            </span>
            <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mt-0.5">
              Creator SaaS
            </span>
          </div>
        </Link>
        <Badge variant="sandbox" className="text-[10px] py-0 px-1.5">
          v1.0
        </Badge>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        <div className="px-2 pb-2 text-[11px] font-bold uppercase tracking-wider text-slate-600">
          Creator Platform
        </div>
        {navigationItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-violet-50 text-violet-700 shadow-sm font-semibold"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive ? "text-violet-600" : "text-slate-400 group-hover:text-slate-600"
                  )}
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold text-violet-700">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}

        {/* Admin Navigation (for Admins) */}
        {user?.role === "ADMIN" && (
          <div className="pt-4">
            <div className="px-2 pb-2 text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Administration
            </div>
            <Link
              href="/dashboard/admin"
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname === "/dashboard/admin"
                  ? "bg-violet-50 text-violet-700 font-semibold"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <ShieldAlert className="h-4 w-4 text-slate-400 group-hover:text-slate-600" />
              <span>Admin Console</span>
            </Link>
          </div>
        )}
      </div>

      {/* Footer Banner */}
      <div className="border-t border-slate-100 p-4">
        <div className="rounded-xl bg-gradient-subtle border border-violet-100 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-violet-900">
            <Zap className="h-4 w-4 text-violet-600" />
            <span>Public Media Kit</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            Share your live verified statistics and brand rates with 1 link.
          </p>
          <Link
            href="/kit/alexrivera"
            target="_blank"
            className="mt-2.5 inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-700 hover:underline"
          >
            <span>Preview Media Kit</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </aside>
  );
}
