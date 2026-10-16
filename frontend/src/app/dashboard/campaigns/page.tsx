"use client";

import React, { useState, useEffect } from "react";
import {
  Briefcase,
  Plus,
  Search,
  Filter,
  DollarSign,
  Calendar,
  CheckCircle2,
  Clock,
  ArrowRight,
  Send,
  ExternalLink,
  MessageSquare
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { BrandCampaign, CampaignApplication } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils";

export default function MarketplaceCampaignsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"browse" | "my-applications">("browse");
  const [campaigns, setCampaigns] = useState<BrandCampaign[]>([]);
  const [myApplications, setMyApplications] = useState<CampaignApplication[]>([]);
  const [selectedNiche, setSelectedNiche] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  // Apply Modal State
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<BrandCampaign | null>(null);
  const [pitchText, setPitchText] = useState("");
  const [proposedRate, setProposedRate] = useState(500);
  const [applying, setApplying] = useState(false);

  // Brand: Create Campaign Modal
  const [createCampaignOpen, setCreateCampaignOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newNiche, setNewNiche] = useState("Tech");
  const [newMin, setNewMin] = useState(400);
  const [newMax, setNewMax] = useState(900);
  const [newDeliverables, setNewDeliverables] = useState("1x Dedicated Reel (60s), 2x Story Frames");
  const [newDeadlineDays, setNewDeadlineDays] = useState(21);
  const [creating, setCreating] = useState(false);

  // Deliverable submission modal
  const [deliverableModalOpen, setDeliverableModalOpen] = useState(false);
  const [targetAppId, setTargetAppId] = useState<string | null>(null);
  const [liveUrl, setLiveUrl] = useState("");
  const [submittingDeliv, setSubmittingDeliv] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedNiche]);

  const loadData = async () => {
    try {
      const [camps, apps] = await Promise.all([
        api.listCampaigns(selectedNiche === "all" ? undefined : selectedNiche),
        api.getMyApplications().catch(() => [])
      ]);
      setCampaigns(camps);
      setMyApplications(apps);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenApply = (camp: BrandCampaign) => {
    setSelectedCampaign(camp);
    setProposedRate(camp.budget_min);
    setPitchText(
      `Hi ${camp.brand_name || "Team"}! My audience loves tech and lifestyle tools. I'd love to produce an aesthetic high-converting Reel highlighting the core features.`
    );
    setApplyModalOpen(true);
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCampaign) return;
    setApplying(true);
    try {
      await api.applyToCampaign(selectedCampaign.id, {
        pitch_text: pitchText,
        proposed_rate: Number(proposedRate),
      });
      setApplyModalOpen(false);
      loadData();
      setActiveTab("my-applications");
    } finally {
      setApplying(false);
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const deadline = new Date();
      deadline.setDate(deadline.getDate() + Number(newDeadlineDays));

      await api.createCampaign({
        title: newTitle,
        description: newDesc,
        niche: newNiche,
        budget_min: Number(newMin),
        budget_max: Number(newMax),
        required_deliverables: newDeliverables.split(",").map((d) => d.trim()),
        submission_deadline: deadline.toISOString(),
      });
      setCreateCampaignOpen(false);
      loadData();
    } finally {
      setCreating(false);
    }
  };

  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetAppId) return;
    setSubmittingDeliv(true);
    try {
      await api.submitDeliverable(targetAppId, {
        deliverable_type: "REEL",
        live_url: liveUrl
      });
      setDeliverableModalOpen(false);
      setLiveUrl("");
      loadData();
    } finally {
      setSubmittingDeliv(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Brand Collaboration Marketplace
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Discover verified paid brand sponsorship briefs or publish campaign requirements.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {(user?.role === "BRAND" || user?.role === "ADMIN") && (
            <Button variant="gradient" onClick={() => setCreateCampaignOpen(true)} className="h-10">
              <Plus className="h-4 w-4 mr-1.5" />
              <span>Post New Campaign</span>
            </Button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("browse")}
          className={`py-3 px-5 border-b-2 font-semibold text-sm transition-colors ${
            activeTab === "browse"
              ? "border-violet-600 text-violet-700 bg-violet-50/40"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Explore Opportunities ({campaigns.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("my-applications")}
          className={`py-3 px-5 border-b-2 font-semibold text-sm transition-colors ${
            activeTab === "my-applications"
              ? "border-violet-600 text-violet-700 bg-violet-50/40"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>My Pitches & Deliverables ({myApplications.length})</span>
        </button>
      </div>

      {/* Tab 1: Browse Campaigns */}
      {activeTab === "browse" && (
        <div className="space-y-6">
          {/* Niche Filter Bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 text-xs">
            <span className="font-semibold text-slate-500 mr-2 flex items-center gap-1">
              <Filter className="h-3.5 w-3.5" /> Category:
            </span>
            {["all", "Tech", "Productivity", "Lifestyle", "Fashion", "Fitness"].map((n) => (
              <button
                key={n}
                onClick={() => setSelectedNiche(n)}
                className={`px-3 py-1.5 rounded-full font-semibold transition-colors ${
                  selectedNiche === n
                    ? "bg-violet-600 text-white shadow-sm"
                    : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {n === "all" ? "All Niches" : n}
              </button>
            ))}
          </div>

          {/* Campaign Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {campaigns.length === 0 ? (
              <Card className="col-span-2 p-12 text-center text-slate-500">
                <Briefcase className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                <p className="text-sm">No campaigns currently available in this category.</p>
              </Card>
            ) : (
              campaigns.map((camp) => (
                <Card key={camp.id} className="p-6 flex flex-col justify-between hover:border-violet-300">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-xs font-semibold text-violet-600 uppercase tracking-wider">
                          {camp.brand_name || "Verified Brand"}
                        </span>
                        <h3 className="text-base font-bold text-slate-900 mt-0.5 leading-snug">
                          {camp.title}
                        </h3>
                      </div>
                      <Badge variant="default" className="text-[10px]">
                        {camp.niche}
                      </Badge>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      {camp.description}
                    </p>

                    <div className="space-y-1 pt-1">
                      <span className="text-[11px] font-semibold text-slate-700 block">Deliverables Required:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {camp.required_deliverables.map((deliv, idx) => (
                          <span key={idx} className="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700 font-medium">
                            {deliv}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-slate-100 pt-4 mt-5 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-slate-600 uppercase font-bold block">Budget Range</span>
                      <span className="text-base font-black text-slate-900">
                        {formatCurrency(camp.budget_min)} – {formatCurrency(camp.budget_max)}
                      </span>
                    </div>

                    <Button variant="gradient" size="sm" onClick={() => handleOpenApply(camp)}>
                      Pitch Deliverable &rarr;
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 2: My Applications */}
      {activeTab === "my-applications" && (
        <div className="space-y-4">
          <h3 className="text-base font-bold text-slate-900">Your Submitted Proposals ({myApplications.length})</h3>

          {myApplications.length === 0 ? (
            <Card className="p-12 text-center text-slate-500">
              <Briefcase className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-sm">You haven&apos;t pitched any campaigns yet.</p>
              <Button variant="gradient" size="sm" onClick={() => setActiveTab("browse")} className="mt-3">
                Browse Active Briefs
              </Button>
            </Card>
          ) : (
            <div className="space-y-4">
              {myApplications.map((app) => (
                <Card key={app.id} className="p-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">
                          {app.campaign_title || "Brand Partnership Brief"}
                        </span>
                        <Badge
                          variant={app.status === "ACCEPTED" ? "success" : app.status === "APPLIED" ? "warning" : "default"}
                          className="text-[10px]"
                        >
                          {app.status}
                        </Badge>
                      </div>

                      <p className="text-xs text-slate-600 italic">
                        &quot;{app.pitch_text}&quot;
                      </p>

                      <div className="text-xs text-slate-500 flex items-center gap-4">
                        <span>Quoted Rate: <strong>${app.proposed_rate}</strong></span>
                        <span>•</span>
                        <span>Submitted on {new Date(app.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {app.status === "ACCEPTED" && (
                        <Button
                          variant="gradient"
                          size="sm"
                          onClick={() => {
                            setTargetAppId(app.id);
                            setDeliverableModalOpen(true);
                          }}
                        >
                          Submit Content Link &rarr;
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Apply / Pitch */}
      <Modal
        isOpen={applyModalOpen}
        onClose={() => setApplyModalOpen(false)}
        title={selectedCampaign ? `Pitch ${selectedCampaign.brand_name || "Brand"}` : "Submit Proposal"}
        description="Share your creative angle and quoted rate."
      >
        <form onSubmit={handleApply} className="space-y-4 text-xs">
          <Input
            label="Quoted Rate ($ USD)"
            type="number"
            value={proposedRate}
            onChange={(e) => setProposedRate(Number(e.target.value))}
            min={10}
            required
          />

          <Textarea
            label="Creator Pitch & Creative Concept"
            value={pitchText}
            onChange={(e) => setPitchText(e.target.value)}
            rows={4}
            required
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="secondary" onClick={() => setApplyModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="gradient" isLoading={applying}>
              <Send className="h-4 w-4 mr-1.5" />
              <span>Send Pitch to Brand</span>
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Create Campaign (Brands) */}
      <Modal
        isOpen={createCampaignOpen}
        onClose={() => setCreateCampaignOpen(false)}
        title="Post New Brand Collaboration Brief"
        description="Invite creators to pitch deliverables tailored for your product."
      >
        <form onSubmit={handleCreateCampaign} className="space-y-4 text-xs">
          <Input
            label="Campaign Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="e.g. Wireless Audio Headphone Desk Setup Review"
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Niche / Category"
              value={newNiche}
              onChange={(e) => setNewNiche(e.target.value)}
              placeholder="Tech"
              required
            />
            <Input
              label="Timeline (Days Open)"
              type="number"
              value={newDeadlineDays}
              onChange={(e) => setNewDeadlineDays(Number(e.target.value))}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Min Compensation ($)"
              type="number"
              value={newMin}
              onChange={(e) => setNewMin(Number(e.target.value))}
              required
            />
            <Input
              label="Max Compensation ($)"
              type="number"
              value={newMax}
              onChange={(e) => setNewMax(Number(e.target.value))}
              required
            />
          </div>

          <Input
            label="Required Deliverables (comma separated)"
            value={newDeliverables}
            onChange={(e) => setNewDeliverables(e.target.value)}
            placeholder="1x Reel, 2x Stories"
            required
          />

          <Textarea
            label="Detailed Campaign Brief"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Explain guidelines, messaging, and review expectations..."
            required
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="secondary" onClick={() => setCreateCampaignOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="gradient" isLoading={creating}>
              Publish Campaign Brief &rarr;
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Submit Deliverable URL */}
      <Modal
        isOpen={deliverableModalOpen}
        onClose={() => setDeliverableModalOpen(false)}
        title="Submit Live Deliverable Link"
        description="Submit your published Instagram Reel link or draft preview for brand verification."
      >
        <form onSubmit={handleSubmitDeliverable} className="space-y-4 text-xs">
          <Input
            label="Live Instagram Post / Reel URL"
            value={liveUrl}
            onChange={(e) => setLiveUrl(e.target.value)}
            placeholder="https://www.instagram.com/reel/Cxyz123..."
            required
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="secondary" onClick={() => setDeliverableModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="gradient" isLoading={submittingDeliv}>
              Submit for Brand Review &rarr;
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
