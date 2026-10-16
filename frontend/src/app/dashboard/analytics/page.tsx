"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Calendar,
  Globe,
  Users,
  Award
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from "recharts";
import { api } from "@/lib/api";
import { AnalyticsResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/utils";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<"30d" | "7d">("30d");

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="py-20 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-t-transparent mx-auto" />
        <span className="text-xs font-semibold text-slate-500 mt-3 block">Loading audience metrics...</span>
      </div>
    );
  }

  const chartPoints = timeRange === "7d" ? data.time_series.slice(-7) : data.time_series;

  return (
    <div className="space-y-8 max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Creator Analytics & Performance
            </h1>
            {data.summary.is_sandbox ? (
              <Badge variant="sandbox">Demo Sandbox Data</Badge>
            ) : (
              <Badge variant="success">Live Meta Verified</Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Real-time follower velocity, reach ratios, and content conversion metrics.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg p-1 text-xs">
          <button
            onClick={() => setTimeRange("7d")}
            className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
              timeRange === "7d" ? "bg-violet-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            Last 7 Days
          </button>
          <button
            onClick={() => setTimeRange("30d")}
            className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
              timeRange === "30d" ? "bg-violet-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            Last 30 Days
          </button>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card>
          <CardHeader className="pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Followers Count</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(data.summary.followers_count)}
            </div>
            <div className="text-xs text-emerald-600 font-semibold mt-1">
              +{formatNumber(data.summary.followers_growth_30d)} in past 30 days
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">30-Day Total Reach</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(data.summary.reach_30d)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Across Reels and feed carousels
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Impressions</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {formatNumber(data.summary.impressions_30d)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              1.65x Repeat view velocity
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avg. Engagement Rate</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-slate-900">
              {data.summary.avg_engagement_rate}%
            </div>
            <div className="text-xs text-emerald-600 font-semibold mt-1">
              Top Tier Creator benchmark
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart: Follower Growth & Reach Over Time */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Follower Growth Velocity & Reach</CardTitle>
            <CardDescription className="text-xs">
              Daily follower count and organic post reach.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartPoints} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorReach" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#7C3AED" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#FFFFFF", borderRadius: "12px", border: "1px solid #E2E8F0", fontSize: "12px" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="reach"
                    stroke="#7C3AED"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorReach)"
                    name="Daily Reach"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Demographics Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-violet-600" />
              <CardTitle className="text-base">Audience Age & Gender</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Demographic breakdown based on verified followers.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-700 block">Age Distribution</span>
              {Object.entries(data.demographics.age_distribution).map(([age, pct]) => (
                <div key={age} className="space-y-1">
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{age}</span>
                    <span className="font-semibold text-slate-900">{pct}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full bg-gradient-woka rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-100">
              <span className="text-xs font-semibold text-slate-700 block mb-2">Gender Breakdown</span>
              <div className="flex items-center justify-between text-xs text-slate-600">
                {Object.entries(data.demographics.gender_distribution).map(([g, val]) => (
                  <div key={g} className="text-center">
                    <span className="block font-bold text-slate-900">{val}%</span>
                    <span className="text-[11px] text-slate-500">{g}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Performing Posts Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900">Top Performing Posts & Reels</h3>
          <span className="text-xs text-slate-500">Sorted by engagement rate</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {data.top_posts.map((post) => (
            <Card key={post.id} className="overflow-hidden hover:border-violet-300">
              <div className="relative aspect-video w-full overflow-hidden bg-slate-100">
                <img
                  src={post.media_url}
                  alt={post.caption}
                  className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                />
                <div className="absolute top-2 right-2">
                  <Badge variant="gradient" className="text-[10px]">
                    {post.engagement_rate}% ER
                  </Badge>
                </div>
              </div>
              <CardContent className="p-4 space-y-3">
                <p className="text-xs text-slate-800 line-clamp-2 italic">
                  &quot;{post.caption}&quot;
                </p>

                <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-3">
                  <div className="flex items-center gap-1.5">
                    <Heart className="h-3.5 w-3.5 text-rose-500" />
                    <span>{post.like_count.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MessageCircle className="h-3.5 w-3.5 text-violet-600" />
                    <span>{post.comments_count.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Eye className="h-3.5 w-3.5 text-blue-500" />
                    <span>{formatNumber(post.reach)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
