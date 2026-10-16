"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Bot,
  Zap,
  BarChart3,
  Sparkles,
  Share2,
  Briefcase,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Instagram,
  Play,
  Calculator,
  Flame,
  Award,
  Film
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";

export default function LandingPage() {
  const [followerCount, setFollowerCount] = useState<number>(45000);
  const [engagementRate, setEngagementRate] = useState<number>(4.2);

  // Dynamic estimate formula
  const estimatedReelRate = Math.round((followerCount / 1000) * 10 * (engagementRate / 3.0));
  const estimatedDMsSavedPerMonth = Math.round((followerCount * 0.035 * 4));

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-violet-100 selection:text-violet-900">
      {/* Top Announcement Bar */}
      <div className="bg-slate-900 px-4 py-2 text-center text-xs text-slate-300">
        <span className="inline-flex items-center gap-1.5 font-medium">
          <Badge variant="sandbox" className="text-[10px] py-0 px-1.5">
            New: Reel Intelligence
          </Badge>
          AI-Powered Instagram Reel Video Pacing, Hook Strength & 8-Dimension Auditing.
          <Link href="/dashboard/reel-intelligence" className="text-violet-400 hover:underline font-semibold ml-1">
            Analyze a Reel &rarr;
          </Link>
        </span>
      </div>

      {/* Navigation Header */}
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-woka shadow-md shadow-violet-500/20 text-white font-bold text-lg">
              W
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-xl tracking-tight text-slate-900">Woka</span>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest -mt-0.5">
                Creator SaaS
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <Link href="/dashboard/reel-intelligence" className="hover:text-slate-900 transition-colors flex items-center gap-1.5 font-semibold text-violet-600">
              <Film className="h-4 w-4" /> Reel Intelligence
            </Link>
            <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
            <a href="#calculator" className="hover:text-slate-900 transition-colors">Rate Calculator</a>
            <a href="#marketplace" className="hover:text-slate-900 transition-colors">Brand Marketplace</a>
            <a href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="gradient" size="sm">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-24 sm:pt-24 sm:pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50/80 px-4 py-1.5 text-xs font-semibold text-violet-700 shadow-sm mb-6">
            <Sparkles className="h-3.5 w-3.5 text-violet-600" />
            <span>The All-In-One Workspace for High-Growth Creators</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 max-w-4xl mx-auto leading-[1.15]">
            Grow smarter, automate Instagram DMs, and <span className="text-woka-gradient">monetize brand deals</span>.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Stop losing hours sending manual DMs on viral Reels. Woka automates your comment-to-DM triggers, verifies your audience analytics, and pitches your rate card directly to top brands.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/register">
              <Button variant="gradient" size="lg" className="h-12 px-8 text-base shadow-lg shadow-violet-500/25">
                <span>Start Free Workspace</span>
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary" size="lg" className="h-12 px-6 text-base">
                <Play className="h-4 w-4 mr-2 text-violet-600" />
                <span>Explore Live Demo Sandbox</span>
              </Button>
            </Link>
          </div>

          {/* Trust Badges */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <Film className="h-4 w-4 text-violet-600" /> 8-Dimension Video & Audio AI Auditing
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-600" /> Official Meta Graph API Ready
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Zero Browser Scraping / Password-Free
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Dynamic Live Media Kit Included
            </span>
          </div>

          {/* Hero Feature Showcase Card */}
          <div className="mt-14 max-w-5xl mx-auto rounded-2xl border border-slate-200/80 bg-white p-3 sm:p-4 shadow-2xl shadow-slate-200/50">
            <div className="rounded-xl border border-slate-100 bg-slate-900 p-6 text-left text-white overflow-hidden relative">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-rose-500" />
                  <div className="h-3 w-3 rounded-full bg-amber-500" />
                  <div className="h-3 w-3 rounded-full bg-emerald-500" />
                  <span className="text-xs font-mono text-slate-400 ml-2">woka://comment-to-dm/realtime-engine</span>
                </div>
                <Badge variant="success" className="text-xs">
                  Trigger Active: 142 DMs Dispatched Today
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Inbound Comment</div>
                  <div className="rounded-lg bg-slate-800/80 border border-slate-700 p-3 text-sm">
                    <span className="font-semibold text-rose-400">@sarah_designs: </span>
                    <span>&quot;Can you send the free toolkit link please? 🔥&quot;</span>
                  </div>
                  <div className="text-xs text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Matched trigger: &quot;toolkit&quot;
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Automated DM Dispatch</div>
                  <div className="rounded-lg bg-violet-950/60 border border-violet-800/60 p-3 text-sm text-violet-200">
                    <span className="font-semibold text-white">Woka Automation: </span>
                    <span>&quot;Hey @sarah_designs! Here is your download link: woka.io/toolkit2026. Enjoy creating!&quot;</span>
                  </div>
                  <div className="text-xs text-slate-400">
                    Response time: 1.2s • Anti-spam frequency passed
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Creator Conversion</div>
                  <div className="rounded-lg bg-slate-800/80 border border-slate-700 p-3 text-sm flex flex-col gap-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Click-through Rate:</span>
                      <span className="font-bold text-white">41.8%</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Leads Generated:</span>
                      <span className="font-bold text-emerald-400">+89 subscribers</span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Logged to Creator Analytics
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Rate Estimator Section */}
      <section id="calculator" className="py-20 bg-white border-y border-slate-200/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <Badge variant="default" className="mb-3">
              Smart Rate Estimator
            </Badge>
            <h2 className="text-3xl font-extrabold text-slate-900">
              Calculate your benchmark brand sponsor rate
            </h2>
            <p className="mt-3 text-slate-600 text-sm">
              Stop guessing. Calculate your standard sponsorship value based on verified audience reach and engagement multiples.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-slate-50 border border-slate-200/80 rounded-2xl p-6 sm:p-10 shadow-sm">
            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-sm font-semibold text-slate-800 mb-2">
                  <span>Instagram Followers</span>
                  <span className="text-violet-600">{formatNumber(followerCount)}</span>
                </div>
                <input
                  type="range"
                  min="5000"
                  max="500000"
                  step="5000"
                  value={followerCount}
                  onChange={(e) => setFollowerCount(Number(e.target.value))}
                  className="w-full accent-violet-600 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-slate-600 mt-1">
                  <span>5k</span>
                  <span>100k</span>
                  <span>500k</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm font-semibold text-slate-800 mb-2">
                  <span>Average Engagement Rate</span>
                  <span className="text-violet-600">{engagementRate}%</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="10.0"
                  step="0.1"
                  value={engagementRate}
                  onChange={(e) => setEngagementRate(Number(e.target.value))}
                  className="w-full accent-rose-500 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-slate-600 mt-1">
                  <span>1.0%</span>
                  <span>4.0% (Average)</span>
                  <span>10.0% (Viral)</span>
                </div>
              </div>

              <div className="rounded-xl bg-white border border-slate-200 p-4 text-xs text-slate-600">
                <span className="font-semibold text-slate-800">Hours Saved Monthly:</span> Woka automates roughly{" "}
                <span className="font-bold text-violet-600">~{estimatedDMsSavedPerMonth} DMs</span> for an audience of this size, saving you over 14 hours every month.
              </div>
            </div>

            <div className="rounded-xl bg-white border border-slate-200 p-6 sm:p-8 flex flex-col justify-between shadow-sm">
              <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Recommended Deliverable Rate
              </span>
              <div className="my-6">
                <div className="text-4xl sm:text-5xl font-black text-slate-900 tracking-tight">
                  ${estimatedReelRate}
                  <span className="text-sm font-medium text-slate-600"> / Reel</span>
                </div>
                <div className="mt-2 text-xs text-emerald-600 font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> Market CPM ~$32.50 per 1,000 Reach
                </div>
              </div>

              <div className="space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-600">
                <div className="flex justify-between">
                  <span>Story Sequence Bundle:</span>
                  <span className="font-bold text-slate-900">${Math.round(estimatedReelRate * 0.45)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Dedicated Full Bundle:</span>
                  <span className="font-bold text-slate-900">${Math.round(estimatedReelRate * 1.55)}</span>
                </div>
              </div>

              <Link href="/register" className="mt-6">
                <Button variant="gradient" className="w-full">
                  Create Verified Media Kit &rarr;
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid Section */}
      <section id="features" className="py-24 max-w-7xl mx-auto px-4 sm:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="default" className="mb-3">
            Core Modules
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900">
            Everything an ambitious creator needs to scale
          </h2>
          <p className="mt-4 text-slate-600">
            Built from scratch for creators, agency managers, and modern brands.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Feature: Reel Intelligence */}
          <Card className="hover:border-violet-300 ring-1 ring-violet-500/20 bg-gradient-to-b from-violet-50/40 to-transparent">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-violet-600 flex items-center justify-center text-white mb-3 shadow-md shadow-violet-500/30">
                <Film className="h-5 w-5" />
              </div>
              <div className="flex items-center justify-between">
                <CardTitle>Woka Reel Intelligence</CardTitle>
                <Badge variant="verified" className="text-[10px]">NEW</Badge>
              </div>
              <CardDescription>
                AI video intelligence engine that scores Reels across 8 dimensions, diagnoses pacing drop-offs, and audits Instagram UI safe zones.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Public URL, MP4 Upload & Meta API modes
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Timestamped scene cuts & speech WPM audit
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Multi-Reel side-by-side benchmark comparison
              </div>
            </CardContent>
          </Card>

          {/* Feature 1 */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-violet-100 flex items-center justify-center text-violet-600 mb-3">
                <Bot className="h-5 w-5" />
              </div>
              <CardTitle>Comment-to-DM Automation</CardTitle>
              <CardDescription>
                Trigger personalized direct messages instantly when fans comment specific keywords on your Reels and Posts.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Keyword exact & substring matching
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Configurable anti-spam cooldowns
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Interactive sandbox testing tool
              </div>
            </CardContent>
          </Card>

          {/* Feature 2 */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-rose-100 flex items-center justify-center text-rose-600 mb-3">
                <BarChart3 className="h-5 w-5" />
              </div>
              <CardTitle>Audience Analytics & Velocity</CardTitle>
              <CardDescription>
                Track follower growth trajectory, reach ratios, and top performing posts with interactive Recharts visualizations.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 30-day time-series growth curves
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Audience age & gender demographics
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Top Reels engagement sorting
              </div>
            </CardContent>
          </Card>

          {/* Feature 3 */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 mb-3">
                <Sparkles className="h-5 w-5" />
              </div>
              <CardTitle>AI Content Studio</CardTitle>
              <CardDescription>
                Generate viral Reels hooks, engaging captions, and smart reach-tiered hashtag buckets in seconds.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 5 Viral hook frameworks
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Tone selector (Witty, Storytelling)
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 1-click clipboard copying
              </div>
            </CardContent>
          </Card>

          {/* Feature 4 */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 mb-3">
                <Share2 className="h-5 w-5" />
              </div>
              <CardTitle>Live Verified Media Kit</CardTitle>
              <CardDescription>
                Ditch outdated PDF media kits. Share a live, mobile-optimized link with verified stats and instant brand inquiries.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Dedicated vanity URL: /kit/[handle]
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Standard deliverable rate cards
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Direct brand contact inquiry form
              </div>
            </CardContent>
          </Card>

          {/* Feature 5 */}
          <Card id="marketplace" className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-600 mb-3">
                <Briefcase className="h-5 w-5" />
              </div>
              <CardTitle>Brand Marketplace</CardTitle>
              <CardDescription>
                Discover active sponsorship campaigns, pitch your proposal directly to brand leads, and submit deliverables for review.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Verified sponsor budget ranges
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Deliverables milestone checklist
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Brand revision feedback loops
              </div>
            </CardContent>
          </Card>

          {/* Feature 6 */}
          <Card className="hover:border-violet-300">
            <CardHeader>
              <div className="h-10 w-10 rounded-xl bg-violet-100 flex items-center justify-center text-violet-600 mb-3">
                <Award className="h-5 w-5" />
              </div>
              <CardTitle>Invoicing & Billing</CardTitle>
              <CardDescription>
                Create professional brand invoices, track payment status (Draft, Sent, Paid), and export clean PDF/print records.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Multi-item sponsor billing
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Auto-calculated tax & subtotals
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 1-Click invoice status updates
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-slate-100/60 border-t border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <Badge variant="default" className="mb-3">
              Simple Pricing
            </Badge>
            <h2 className="text-3xl font-extrabold text-slate-900">
              Plans that scale with your creator career
            </h2>
            <p className="mt-3 text-slate-600 text-sm">
              Start free today with no credit card required. Upgrade when your engagement takes off.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Free Plan */}
            <Card className="flex flex-col justify-between">
              <CardHeader>
                <span className="text-xs font-bold text-slate-600 uppercase">Starter</span>
                <CardTitle className="text-2xl mt-1">Free Tier</CardTitle>
                <div className="mt-4 text-3xl font-extrabold text-slate-900">$0<span className="text-sm font-normal text-slate-600">/mo</span></div>
                <CardDescription className="mt-2">Perfect for exploring automations and setting up your media kit.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-slate-600 flex-1">
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 1 Instagram Account</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 50 Comment-to-DMs / month</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 10 AI Studio generations</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Basic Growth Analytics</div>
              </CardContent>
              <div className="p-6 pt-0">
                <Link href="/register">
                  <Button variant="secondary" className="w-full">
                    Get Started Free
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Pro Plan */}
            <Card className="border-violet-500 shadow-xl shadow-violet-500/10 relative flex flex-col justify-between">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge variant="gradient" className="px-3 py-1">
                  Most Popular
                </Badge>
              </div>
              <CardHeader>
                <span className="text-xs font-bold text-violet-600 uppercase">Pro Creator</span>
                <CardTitle className="text-2xl mt-1">Growth Pro</CardTitle>
                <div className="mt-4 text-3xl font-extrabold text-slate-900">$29<span className="text-sm font-normal text-slate-600">/mo</span></div>
                <CardDescription className="mt-2">For active creators monetizing their viral Reels and audience engagement.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-slate-600 flex-1">
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 3 Instagram Accounts</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 2,000 Comment-to-DMs / month</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 500 AI Studio generations</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Full Recharts Analytics & Reach</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Public Verified Media Kit</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Brand Marketplace Access</div>
              </CardContent>
              <div className="p-6 pt-0">
                <Link href="/register">
                  <Button variant="gradient" className="w-full">
                    Start 14-Day Pro Trial
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Agency Plan */}
            <Card className="flex flex-col justify-between">
              <CardHeader>
                <span className="text-xs font-bold text-slate-600 uppercase">Agency & Brands</span>
                <CardTitle className="text-2xl mt-1">Scale Agency</CardTitle>
                <div className="mt-4 text-3xl font-extrabold text-slate-900">$99<span className="text-sm font-normal text-slate-600">/mo</span></div>
                <CardDescription className="mt-2">For talent managers, agencies, and brands running multi-creator campaigns.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-slate-600 flex-1">
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Unlimited Instagram Accounts</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 20,000 Comment-to-DMs / month</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 5,000 AI Studio generations</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Brand Campaign Creation</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Deliverables Approval Workflows</div>
                <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Priority Support</div>
              </CardContent>
              <div className="p-6 pt-0">
                <Link href="/register">
                  <Button variant="secondary" className="w-full">
                    Contact for Agency
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-woka text-white font-bold text-sm">
              W
            </div>
            <span className="font-extrabold text-slate-900 tracking-tight">Woka</span>
            <span className="text-xs text-slate-600 ml-2">© 2026 Woka Platform Inc. All rights reserved.</span>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs text-slate-600">
            <Link href="/login" className="hover:text-slate-900">Sign In</Link>
            <Link href="/register" className="hover:text-slate-900">Sign Up</Link>
            <Link href="/kit/alexrivera" target="_blank" className="hover:text-slate-900">Demo Media Kit</Link>
            <Link href="/privacy" className="hover:text-slate-900">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-slate-900">Terms of Service</Link>
            <Link href="/deletion-status" className="hover:text-slate-900">Data Deletion</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
