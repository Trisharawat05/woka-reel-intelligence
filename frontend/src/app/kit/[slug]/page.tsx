"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  MapPin,
  Instagram,
  Eye,
  TrendingUp,
  Users,
  CheckCircle2,
  Send,
  Sparkles,
  ArrowRight,
  ExternalLink
} from "lucide-react";
import { api } from "@/lib/api";
import { CreatorProfile } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/dialog";
import { formatNumber, formatCurrency } from "@/lib/utils";

export default function PublicMediaKitPage() {
  const params = useParams();
  const slug = (params?.slug as string) || "alexrivera";
  const [profile, setProfile] = useState<CreatorProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Inquiry Modal State
  const [inquiryModalOpen, setInquiryModalOpen] = useState(false);
  const [brandName, setBrandName] = useState("");
  const [email, setEmail] = useState("");
  const [budget, setBudget] = useState("$500 - $1,000");
  const [scope, setScope] = useState("Dedicated Instagram Reel");
  const [message, setMessage] = useState("");
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  const [inquirySuccess, setInquirySuccess] = useState(false);

  useEffect(() => {
    api.getPublicProfile(slug)
      .then(setProfile)
      .catch((err) => setError(err.message || "Creator media kit not found"))
      .finally(() => setLoading(false));
  }, [slug]);

  const handleSendInquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingInquiry(true);
    try {
      await api.submitInquiry(slug, {
        brand_name: brandName,
        contact_email: email,
        budget,
        project_scope: scope,
        message,
      });
      setInquirySuccess(true);
      setTimeout(() => {
        setInquirySuccess(false);
        setInquiryModalOpen(false);
        setBrandName("");
        setEmail("");
        setMessage("");
      }, 3000);
    } finally {
      setSubmittingInquiry(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-t-transparent" />
          <span className="text-xs font-semibold text-slate-500">Loading verified creator media kit...</span>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full p-8 text-center space-y-4">
          <h2 className="text-xl font-bold text-slate-900">Media Kit Not Available</h2>
          <p className="text-sm text-slate-500">{error || "This creator profile is private or does not exist."}</p>
          <Link href="/">
            <Button variant="secondary" className="w-full">
              Explore Woka &rarr;
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-violet-100 selection:text-violet-900 pb-24">
      {/* Top Banner */}
      <div className="border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-woka text-white font-bold text-xs">
              W
            </div>
            <span className="font-extrabold text-sm tracking-tight text-slate-900">Woka Media Kit</span>
          </Link>

          <Button variant="gradient" size="sm" onClick={() => setInquiryModalOpen(true)}>
            Work With Me &rarr;
          </Button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-8 pt-10 space-y-8">
        {/* Creator Profile Header */}
        <div className="rounded-3xl border border-slate-200/80 bg-white p-6 sm:p-10 shadow-sm relative overflow-hidden">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
              <img
                src={profile.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200"}
                alt={profile.display_name}
                className="h-24 w-24 rounded-full border-4 border-violet-100 object-cover shadow-md"
              />
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    {profile.display_name}
                  </h1>
                  <Badge variant="verified" className="flex items-center gap-1 text-xs">
                    <ShieldCheck className="h-3.5 w-3.5 text-violet-600" />
                    <span>Verified Creator</span>
                  </Badge>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1">
                    <Instagram className="h-3.5 w-3.5 text-rose-500" />
                    <span>@{profile.slug}</span>
                  </span>
                  {profile.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 text-slate-400" />
                      <span>{profile.location}</span>
                    </span>
                  )}
                </div>

                <p className="text-sm text-slate-600 max-w-xl leading-relaxed pt-1">
                  {profile.bio}
                </p>

                <div className="flex flex-wrap gap-1.5 pt-2">
                  {profile.niches.map((n) => (
                    <span key={n} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                      {n}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <Button variant="gradient" size="lg" onClick={() => setInquiryModalOpen(true)} className="w-full sm:w-auto h-11 shadow-md">
              <span>Send Campaign Proposal</span>
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </div>

        {/* Verified Performance Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <Card className="hover:border-violet-300">
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Audience Followers
              </span>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black text-slate-900">
                {formatNumber(profile.followers_count)}
              </div>
              <div className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Meta API Verified Count
              </div>
            </CardContent>
          </Card>

          <Card className="hover:border-violet-300">
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Avg. Engagement Rate
              </span>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black text-slate-900">
                {profile.engagement_rate}%
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Based on active Reels and Carousel posts
              </div>
            </CardContent>
          </Card>

          <Card className="hover:border-violet-300">
            <CardHeader className="pb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Monthly Organic Reach
              </span>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black text-slate-900">
                {formatNumber(profile.total_reach_30d)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                3.4x Audience Multiplier
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Standard Sponsorship Rate Cards */}
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Standard Deliverable Rate Cards</h2>
            <p className="text-xs text-slate-500">
              Standard commercial baseline rates. Multi-deliverable packages and exclusivity options available upon request.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1 */}
            <Card className="flex flex-col justify-between hover:border-violet-300">
              <CardHeader>
                <span className="text-xs font-bold text-slate-400 uppercase">Single Asset</span>
                <CardTitle className="text-lg mt-1">Dedicated 60s Reel</CardTitle>
                <div className="text-3xl font-black text-slate-900 mt-3">
                  {formatCurrency(profile.rate_reel)}
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  High-production 4K Reel featuring your brand, narrative hook, and bio link placement.
                </p>
              </CardHeader>
              <div className="p-6 pt-0">
                <Button
                  variant="secondary"
                  className="w-full text-xs"
                  onClick={() => {
                    setScope("Dedicated 60s Reel");
                    setInquiryModalOpen(true);
                  }}
                >
                  Select Deliverable
                </Button>
              </div>
            </Card>

            {/* Card 2 */}
            <Card className="flex flex-col justify-between hover:border-violet-300">
              <CardHeader>
                <span className="text-xs font-bold text-slate-400 uppercase">Story Sequence</span>
                <CardTitle className="text-lg mt-1">3x Instagram Stories</CardTitle>
                <div className="text-3xl font-black text-slate-900 mt-3">
                  {formatCurrency(profile.rate_story)}
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  3 continuous story frames with direct sticker links and brand tag.
                </p>
              </CardHeader>
              <div className="p-6 pt-0">
                <Button
                  variant="secondary"
                  className="w-full text-xs"
                  onClick={() => {
                    setScope("3x Instagram Stories");
                    setInquiryModalOpen(true);
                  }}
                >
                  Select Deliverable
                </Button>
              </div>
            </Card>

            {/* Card 3 */}
            <Card className="border-violet-400 shadow-md flex flex-col justify-between relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge variant="gradient" className="text-[10px]">
                  Recommended Bundle
                </Badge>
              </div>
              <CardHeader>
                <span className="text-xs font-bold text-violet-600 uppercase">Full Campaign</span>
                <CardTitle className="text-lg mt-1">Reel + Story + Link Bundle</CardTitle>
                <div className="text-3xl font-black text-slate-900 mt-3">
                  {formatCurrency(profile.rate_bundle)}
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  1x Dedicated Reel, 2x Story frames, and 7-day link-in-bio placement for maximum conversion.
                </p>
              </CardHeader>
              <div className="p-6 pt-0">
                <Button
                  variant="gradient"
                  className="w-full text-xs"
                  onClick={() => {
                    setScope("Full Package Bundle");
                    setInquiryModalOpen(true);
                  }}
                >
                  Book Bundle &rarr;
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Inquiry Modal */}
      <Modal
        isOpen={inquiryModalOpen}
        onClose={() => setInquiryModalOpen(false)}
        title={`Collaborate with ${profile.display_name}`}
        description="Submit your campaign brief and budget to receive a response within 24 hours."
      >
        {inquirySuccess ? (
          <div className="py-8 text-center space-y-2">
            <CheckCircle2 className="h-10 w-10 text-emerald-600 mx-auto" />
            <h4 className="font-bold text-base text-slate-900">Inquiry Sent Successfully!</h4>
            <p className="text-xs text-slate-500">
              {profile.display_name} has received your proposal and will reply directly to your contact email.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSendInquiry} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Company / Brand Name"
                placeholder="Lumin Audio"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                required
              />
              <Input
                label="Work Email Address"
                type="email"
                placeholder="partnerships@brand.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                  Deliverable Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                >
                  <option value="Dedicated Instagram Reel">Dedicated 60s Reel</option>
                  <option value="3x Instagram Stories">3x Instagram Stories</option>
                  <option value="Full Package Bundle">Full Package Bundle</option>
                  <option value="Custom Project">Custom Partnership</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                  Budget Range
                </label>
                <select
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                >
                  <option value="$300 - $600">$300 - $600</option>
                  <option value="$600 - $1,500">$600 - $1,500</option>
                  <option value="$1,500 - $5,000">$1,500 - $5,000</option>
                  <option value="$5,000+">$5,000+</option>
                </select>
              </div>
            </div>

            <Textarea
              label="Campaign Brief & Objectives"
              placeholder="Tell the creator about the product, timeline, key messaging, and expectations..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
            />

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
              <Button type="button" variant="secondary" onClick={() => setInquiryModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="gradient" isLoading={submittingInquiry}>
                <Send className="h-4 w-4 mr-1.5" />
                <span>Submit Proposal</span>
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
