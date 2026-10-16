"use client";

import React, { useState } from "react";
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
  X
} from "lucide-react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

const navigationItems = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Instagram Sync", href: "/dashboard/instagram", icon: Instagram },
  { name: "Automations", href: "/dashboard/automations", icon: Bot },
  { name: "Analytics & Reach", href: "/dashboard/analytics", icon: BarChart3 },
  { name: "AI Content Studio", href: "/dashboard/ai-studio", icon: Sparkles },
  { name: "Media Kit & Rates", href: "/dashboard/media-kit", icon: Share2 },
  { name: "Brand Marketplace", href: "/dashboard/campaigns", icon: Briefcase },
  { name: "Invoices & Rates", href: "/dashboard/invoices", icon: Receipt },
  { name: "Plan & Usage", href: "/dashboard/billing", icon: CreditCard },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative flex w-64 flex-col bg-white p-4 shadow-xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <span className="font-extrabold text-lg text-slate-900">Woka</span>
              <button onClick={() => setMobileMenuOpen(false)} className="rounded p-1 text-slate-400">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 flex-1 space-y-1">
              {navigationItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                      isActive
                        ? "bg-violet-50 text-violet-700 font-semibold"
                        : "text-slate-600 hover:bg-slate-50"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col lg:pl-64">
        <Topbar onToggleMobileMenu={() => setMobileMenuOpen(true)} />
        <main className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
