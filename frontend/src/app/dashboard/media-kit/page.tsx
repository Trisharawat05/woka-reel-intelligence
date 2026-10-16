"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Share2,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  DollarSign,
  Globe,
  Tag,
  MapPin,
  CheckCircle2
} from "lucide-react";
import { api } from "@/lib/api";
import { CreatorProfile } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";

export default function MediaKitSettingsPage() {
  const [profile, setProfile] = useState<CreatorProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form states
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [niches, setNiches] = useState("");
  const [location, setLocation] = useState("");
  const [rateReel, setRateReel] = useState(450);
  const [rateStory, setRateStory] = useState(150);
  const [rateBundle, setRateBundle] = useState(550);
  const [isPublic, setIsPublic] = useState(true);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const p = await api.getMyProfile();
      setProfile(p);
      setDisplayName(p.display_name);
      setBio(p.bio || "");
      setNiches(p.niches.join(", "));
      setLocation(p.location || "");
      setRateReel(p.rate_reel);
      setRateStory(p.rate_story);
      setRateBundle(p.rate_bundle);
      setIsPublic(p.is_public);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const nicheArray = niches.split(",").map((n) => n.trim()).filter(Boolean);
      const updated = await api.updateProfile({
        display_name: displayName,
        bio,
        niches: nicheArray,
        location,
        rate_reel: Number(rateReel),
        rate_story: Number(rateStory),
        rate_bundle: Number(rateBundle),
        is_public: isPublic
      });
      setProfile(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const publicUrl = profile ? `${typeof window !== "undefined" ? window.location.origin : ""}/kit/${profile.slug}` : "";

  const copyPublicUrl = () => {
    navigator.clipboard.writeText(publicUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-xs text-slate-500">
        Loading media kit details...
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Public Media Kit & Rate Card
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Your live, verified portfolio link to send to brand partners, sponsors, and PR agencies.
        </p>
      </div>

      {saveSuccess && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>Media kit profile saved successfully! Changes are live on your public link.</span>
        </div>
      )}

      {/* Share Banner */}
      <Card className="border-violet-200 bg-gradient-to-r from-violet-50/70 to-rose-50/70 shadow-sm">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs font-bold text-violet-700 uppercase tracking-wider">
                Live Public Media Kit URL
              </span>
              <div className="font-mono text-sm text-slate-900 font-semibold break-all">
                {publicUrl}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={copyPublicUrl} className="h-9">
                {copiedLink ? <Check className="h-4 w-4 mr-1 text-emerald-600" /> : <Copy className="h-4 w-4 mr-1" />}
                <span>{copiedLink ? "Copied!" : "Copy Link"}</span>
              </Button>
              {profile && (
                <Link href={`/kit/${profile.slug}`} target="_blank">
                  <Button variant="gradient" size="sm" className="h-9">
                    <span>View Live</span>
                    <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Media Kit Configuration</CardTitle>
          <CardDescription className="text-xs">
            Tailor the bio, categories, and standard pricing presented to sponsors.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-6 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Creator Display Name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
              <Input
                label="Location (City, Country)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="San Francisco, CA"
              />
            </div>

            <Textarea
              label="Creator Bio / Editorial Focus"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Tell brands about your audience and style..."
              rows={3}
            />

            <Input
              label="Primary Content Niches (comma separated)"
              value={niches}
              onChange={(e) => setNiches(e.target.value)}
              placeholder="Tech, Productivity, Creator Economy, Lifestyle"
              required
            />

            {/* Standard Deliverable Rates */}
            <div className="border-t border-slate-100 pt-4 space-y-3">
              <span className="font-semibold text-slate-800 text-sm block">Standard Deliverable Rates ($ USD)</span>
              <p className="text-slate-500 text-xs">
                Transparent starting rates help brands qualify their budgets before reaching out.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <Input
                  label="Dedicated 60s Reel"
                  type="number"
                  value={rateReel}
                  onChange={(e) => setRateReel(Number(e.target.value))}
                  min={0}
                  required
                />
                <Input
                  label="Story Sequence (3 frames)"
                  type="number"
                  value={rateStory}
                  onChange={(e) => setRateStory(Number(e.target.value))}
                  min={0}
                  required
                />
                <Input
                  label="Full Package Bundle"
                  type="number"
                  value={rateBundle}
                  onChange={(e) => setRateBundle(Number(e.target.value))}
                  min={0}
                  required
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
              <input
                type="checkbox"
                id="isPublic"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
              />
              <label htmlFor="isPublic" className="text-xs text-slate-700 font-medium">
                Make media kit publicly accessible via vanity link
              </label>
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" variant="gradient" className="h-10 px-8" isLoading={saving}>
                Save Changes &rarr;
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
