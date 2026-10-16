"use client";

import React, { useState, useEffect } from "react";
import {
  CreditCard,
  CheckCircle2,
  Zap,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Bot,
  Sparkles
} from "lucide-react";
import { api } from "@/lib/api";
import { Subscription } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function BillingAndUsagePage() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [upgradeMsg, setUpgradeMsg] = useState<string | null>(null);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    try {
      const data = await api.getSubscription();
      setSub(data);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (targetTier: string) => {
    setUpgrading(true);
    try {
      const updated = await api.upgradeSubscription(targetTier);
      setSub(updated);
      setUpgradeMsg(`Successfully upgraded to ${targetTier} plan! Your new limits are active.`);
      setTimeout(() => setUpgradeMsg(null), 4000);
    } finally {
      setUpgrading(false);
    }
  };

  if (loading || !sub) {
    return (
      <div className="py-20 text-center text-xs text-slate-500">
        Loading subscription and quota metrics...
      </div>
    );
  }

  const dmPercent = Math.min(100, Math.round((sub.dm_used_monthly / sub.dm_limit_monthly) * 100));
  const aiPercent = Math.min(100, Math.round((sub.ai_used_monthly / sub.ai_limit_monthly) * 100));

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Subscription & Usage Quotas
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Monitor your monthly comment automation runs, AI studio tokens, and workspace entitlements.
        </p>
      </div>

      {upgradeMsg && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>{upgradeMsg}</span>
        </div>
      )}

      {/* Real-time Usage Meters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* DM Automations Meter */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-sm">Comment-to-DM Quota</CardTitle>
              <CardDescription className="text-xs">Monthly automated messages</CardDescription>
            </div>
            <div className="h-8 w-8 rounded-lg bg-violet-100 flex items-center justify-center text-violet-600">
              <Bot className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-black text-slate-900">
                {sub.dm_used_monthly.toLocaleString()}{" "}
                <span className="text-sm font-normal text-slate-600">/ {sub.dm_limit_monthly.toLocaleString()}</span>
              </span>
              <span className="text-xs font-bold text-violet-600">{dmPercent}%</span>
            </div>

            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-gradient-woka rounded-full transition-all duration-300"
                style={{ width: `${dmPercent}%` }}
              />
            </div>

            <p className="text-[11px] text-slate-600">
              Resets on {new Date(sub.current_period_end).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>

        {/* AI Generations Meter */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-sm">AI Content Studio Quota</CardTitle>
              <CardDescription className="text-xs">Captions & viral hooks generated</CardDescription>
            </div>
            <div className="h-8 w-8 rounded-lg bg-rose-100 flex items-center justify-center text-rose-600">
              <Sparkles className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-black text-slate-900">
                {sub.ai_used_monthly.toLocaleString()}{" "}
                <span className="text-sm font-normal text-slate-600">/ {sub.ai_limit_monthly.toLocaleString()}</span>
              </span>
              <span className="text-xs font-bold text-rose-600">{aiPercent}%</span>
            </div>

            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-rose-500 to-amber-500 rounded-full transition-all duration-300"
                style={{ width: `${aiPercent}%` }}
              />
            </div>

            <p className="text-[11px] text-slate-600">
              Resets on {new Date(sub.current_period_end).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Plan Tiers */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-900">Available Plans</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Free Tier */}
          <Card className={`p-6 flex flex-col justify-between ${sub.plan_tier === "FREE" ? "border-violet-500 ring-2 ring-violet-500/10" : ""}`}>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase">Starter</span>
                {sub.plan_tier === "FREE" && <Badge variant="default">Current Plan</Badge>}
              </div>
              <h4 className="text-xl font-bold text-slate-900">Free</h4>
              <div className="text-2xl font-black text-slate-900">$0<span className="text-xs font-normal text-slate-400">/mo</span></div>
              <ul className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 1 Instagram Account</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 50 DMs / month</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 10 AI generations</li>
              </ul>
            </div>
            {sub.plan_tier !== "FREE" && (
              <Button variant="secondary" size="sm" className="w-full mt-6" onClick={() => handleUpgrade("FREE")}>
                Downgrade to Free
              </Button>
            )}
          </Card>

          {/* Pro Tier */}
          <Card className={`p-6 flex flex-col justify-between ${sub.plan_tier === "PRO" ? "border-violet-500 ring-2 ring-violet-500/20 shadow-md" : "hover:border-violet-300"}`}>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-violet-600 uppercase">Pro Creator</span>
                {sub.plan_tier === "PRO" && <Badge variant="gradient">Current Plan</Badge>}
              </div>
              <h4 className="text-xl font-bold text-slate-900">Growth Pro</h4>
              <div className="text-2xl font-black text-slate-900">$29<span className="text-xs font-normal text-slate-400">/mo</span></div>
              <ul className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 3 Instagram Accounts</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 2,000 DMs / month</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 500 AI generations</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Public Verified Media Kit</li>
              </ul>
            </div>
            {sub.plan_tier !== "PRO" && (
              <Button variant="gradient" size="sm" className="w-full mt-6" onClick={() => handleUpgrade("PRO")} isLoading={upgrading}>
                Upgrade to Pro &rarr;
              </Button>
            )}
          </Card>

          {/* Agency Tier */}
          <Card className={`p-6 flex flex-col justify-between ${sub.plan_tier === "AGENCY" ? "border-violet-500 ring-2 ring-violet-500/20 shadow-md" : "hover:border-violet-300"}`}>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-600 uppercase">Scale</span>
                {sub.plan_tier === "AGENCY" && <Badge variant="default">Current Plan</Badge>}
              </div>
              <h4 className="text-xl font-bold text-slate-900">Agency & Brand</h4>
              <div className="text-2xl font-black text-slate-900">$99<span className="text-xs font-normal text-slate-400">/mo</span></div>
              <ul className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Unlimited Instagram Accounts</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 20,000 DMs / month</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> 5,000 AI generations</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Brand Campaign Creation</li>
              </ul>
            </div>
            {sub.plan_tier !== "AGENCY" && (
              <Button variant="secondary" size="sm" className="w-full mt-6" onClick={() => handleUpgrade("AGENCY")} isLoading={upgrading}>
                Upgrade to Agency &rarr;
              </Button>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
