"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Film,
  UploadCloud,
  Link as LinkIcon,
  Instagram,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Bookmark,
  TrendingUp,
  Award,
  Zap,
  ArrowRight,
  Sliders,
  Copy,
  Check,
  Search,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  FileVideo,
  AlertCircle
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/utils";
import {
  ReelAnalysisJob,
  ReelReport,
  ReelReportSummary,
  ReelComparison,
  TimelineFinding
} from "@/types";

type ActiveTab = "ANALYZE" | "REPORT" | "HISTORY" | "COMPARE";
type SubmissionMode = "PUBLIC_URL" | "VIDEO_UPLOAD" | "CONNECTED_ACCOUNT";

export default function ReelIntelligencePage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("ANALYZE");
  const [submissionMode, setSubmissionMode] = useState<SubmissionMode>("PUBLIC_URL");

  // Form states
  const [publicUrl, setPublicUrl] = useState("");
  const [declaredViews, setDeclaredViews] = useState("");
  const [declaredLikes, setDeclaredLikes] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);

  // Connected accounts Reels
  const [connectedReels, setConnectedReels] = useState<any[]>([]);
  const [hasConnectedAccount, setHasConnectedAccount] = useState<boolean>(true);
  const [connectedUsername, setConnectedUsername] = useState<string>("");

  // Job & Report states
  const [activeJob, setActiveJob] = useState<ReelAnalysisJob | null>(null);
  const [currentReport, setCurrentReport] = useState<ReelReport | null>(null);
  const [reportsList, setReportsList] = useState<ReelReportSummary[]>([]);
  const [selectedCompareIds, setSelectedCompareIds] = useState<string[]>([]);
  const [comparisonResult, setComparisonResult] = useState<ReelComparison | null>(null);

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTimelineFilter, setActiveTimelineFilter] = useState<string>("ALL");
  const [activeExperimentTab, setActiveExperimentTab] = useState<"HOOKS" | "THUMBNAILS" | "CAPTIONS" | "CTA" | "SCRIPT">("HOOKS");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Load connected Reels and history on mount
  useEffect(() => {
    loadInitialData();
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const [reelsRes, reportsRes] = await Promise.all([
        api.getConnectedReels().catch(() => ({ has_connected_account: false, username: "", is_sandbox: false, reels: [] })),
        api.listReelReports().catch(() => [])
      ]);


      if (reelsRes) {
        setHasConnectedAccount(reelsRes.has_connected_account);
        setConnectedReels(reelsRes.reels || []);
        if (reelsRes.username) setConnectedUsername(reelsRes.username);
      }
      setReportsList(reportsRes || []);

      // If reports exist and none is loaded, pre-load the latest one for instant inspection
      if (reportsRes && reportsRes.length > 0 && !currentReport) {
        loadReport(reportsRes[0].id, false);
      }
    } catch (err: any) {
      console.error("Initial data load error:", err);
    }
  };

  // Poll job status
  const startJobPolling = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const job = await api.getReelJob(jobId);
        setActiveJob(job);

        if (job.status === "COMPLETED" && job.report_id) {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsLoading(false);
          await loadReport(job.report_id, true);
        } else if (job.status === "FAILED") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsLoading(false);
          setErrorMsg(job.error_message || "Reel analysis failed during video decoding or metric retrieval.");
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    }, 1500);
  };

  const loadReport = async (reportId: string, switchTab = true) => {
    try {
      setIsLoading(true);
      const rep = await api.getReelReport(reportId);
      setCurrentReport(rep);
      if (switchTab) {
        setActiveTab("REPORT");
      }
    } catch (err: any) {
      setErrorMsg("Failed to load Reel report: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Submission Handlers
  const handleSubmitPublicUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publicUrl.trim()) return;

    setErrorMsg(null);
    setIsLoading(true);

    try {
      const job = await api.submitPublicReelUrl({
        url: publicUrl.trim(),
        declared_views: declaredViews ? parseInt(declaredViews, 10) : undefined,
        declared_likes: declaredLikes ? parseInt(declaredLikes, 10) : undefined,
      });
      setActiveJob(job);
      startJobPolling(job.id);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMsg(err.message || "Failed to submit Reel URL.");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setFilePreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSubmitUpload = async () => {
    if (!selectedFile) return;

    setErrorMsg(null);
    setIsLoading(true);

    try {
      const job = await api.submitVideoUpload(selectedFile);
      setActiveJob(job);
      startJobPolling(job.id);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMsg(err.message || "Failed to upload video.");
    }
  };

  const handleSubmitConnectedReel = async (reel: any) => {
    setErrorMsg(null);
    setIsLoading(true);

    try {
      const job = await api.submitConnectedReel({
        media_id: reel.media_id,
        title: reel.title,
        caption: reel.caption,
        media_url: reel.media_url,
        thumbnail_url: reel.thumbnail_url,
      });
      setActiveJob(job);
      startJobPolling(job.id);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMsg(err.message || "Failed to analyze connected Reel.");
    }
  };

  const handleRetry = async () => {
    if (!activeJob) return;
    setErrorMsg(null);
    setIsLoading(true);
    try {
      const retried = await api.retryReelJob(activeJob.id);
      setActiveJob(retried);
      startJobPolling(retried.id);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMsg(err.message || "Retry failed.");
    }
  };

  const handleCompareSubmit = async () => {
    if (selectedCompareIds.length < 2) {
      setErrorMsg("Please select at least 2 Reels to compare.");
      return;
    }
    setErrorMsg(null);
    setIsLoading(true);
    try {
      const comp = await api.compareReels(selectedCompareIds);
      setComparisonResult(comp);
      setActiveTab("COMPARE");
    } catch (err: any) {
      setErrorMsg(err.message || "Comparison failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const toggleCompareSelect = (id: string) => {
    if (selectedCompareIds.includes(id)) {
      setSelectedCompareIds(selectedCompareIds.filter((item) => item !== id));
    } else {
      if (selectedCompareIds.length >= 5) return;
      setSelectedCompareIds([...selectedCompareIds, id]);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner & Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Woka Reel Intelligence
            </h1>
            <Badge variant="verified" className="bg-violet-100 text-violet-700 border-violet-200">
              <Sparkles className="w-3 h-3 mr-1" />
              AI Multimodal v2.0
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            End-to-end video understanding, visual framing, hook retention diagnostics, and transparent performance analytics.
          </p>
        </div>

        {/* Global Navigation Tabs */}
        <div className="flex items-center gap-1.5 rounded-xl bg-slate-100 p-1 border border-slate-200">
          <button
            onClick={() => setActiveTab("ANALYZE")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === "ANALYZE"
                ? "bg-white text-violet-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            Analyze Reel
          </button>
          <button
            onClick={() => setActiveTab("REPORT")}
            disabled={!currentReport}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === "REPORT"
                ? "bg-white text-violet-700 shadow-sm"
                : currentReport
                ? "text-slate-600 hover:text-slate-900"
                : "text-slate-400 cursor-not-allowed opacity-60"
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            Report Dashboard
          </button>
          <button
            onClick={() => setActiveTab("HISTORY")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === "HISTORY"
                ? "bg-white text-violet-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            History ({reportsList.length})
          </button>
          <button
            onClick={() => {
              if (selectedCompareIds.length >= 2) handleCompareSubmit();
              else setActiveTab("COMPARE");
            }}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === "COMPARE"
                ? "bg-white text-violet-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Compare {selectedCompareIds.length > 0 && `(${selectedCompareIds.length})`}
          </button>
        </div>
      </div>

      {/* Global Error Alert */}
      {errorMsg && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <p className="font-semibold">Analysis Notice</p>
            <p className="mt-0.5 text-red-700">{errorMsg}</p>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-xs font-semibold text-red-600 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Active Job Processing Stepper Banner */}
      {activeJob && activeJob.status !== "COMPLETED" && (
        <Card className="border-violet-200 bg-gradient-to-r from-violet-50/70 via-white to-rose-50/50 shadow-sm">
          <CardContent className="pt-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-2.5 w-2.5 rounded-full bg-violet-600 animate-pulse" />
                  <span className="font-bold text-slate-900 text-sm">
                    {activeJob.status === "FAILED" ? "Job Failed" : "Analyzing Reel Media..."}
                  </span>
                  <Badge variant="sandbox" className="text-[10px]">
                    Stage: {activeJob.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-600 mt-1">{activeJob.stage_message}</p>
              </div>

              {activeJob.status === "FAILED" && (
                <Button size="sm" onClick={handleRetry} className="bg-red-600 hover:bg-red-700 text-white">
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                  Retry Analysis
                </Button>
              )}
            </div>

            {/* Visual Progress Bar */}
            <div className="mt-4">
              <div className="flex justify-between text-[11px] font-semibold text-slate-500 mb-1">
                <span>Progress</span>
                <span>{activeJob.progress_percent}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full bg-gradient-to-r from-violet-600 to-rose-500 transition-all duration-500 rounded-full"
                  style={{ width: `${Math.max(5, activeJob.progress_percent)}%` }}
                />
              </div>

              {/* Multi-stage Steps */}
              <div className="grid grid-cols-4 gap-2 mt-3 text-center text-[11px] font-medium text-slate-500">
                <span className={activeJob.progress_percent >= 15 ? "text-violet-700 font-semibold" : ""}>
                  1. Ingestion
                </span>
                <span className={activeJob.progress_percent >= 45 ? "text-violet-700 font-semibold" : ""}>
                  2. Visual Pacing
                </span>
                <span className={activeJob.progress_percent >= 70 ? "text-violet-700 font-semibold" : ""}>
                  3. Metrics
                </span>
                <span className={activeJob.progress_percent >= 90 ? "text-violet-700 font-semibold" : ""}>
                  4. AI Diagnosis
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: ANALYZE REEL (SUBMISSION FLOW)                                      */}
      {/* ========================================================================= */}
      {activeTab === "ANALYZE" && (
        <div className="space-y-6">
          {/* Mode Switcher Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              onClick={() => setSubmissionMode("PUBLIC_URL")}
              className={`cursor-pointer rounded-2xl p-5 border transition-all ${
                submissionMode === "PUBLIC_URL"
                  ? "border-violet-600 bg-violet-50/40 shadow-sm ring-1 ring-violet-500"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                  <LinkIcon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Mode A: Public Reel URL</h3>
                  <p className="text-xs text-slate-500">Analyze any public link</p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-600 leading-relaxed">
                Evaluates video pacing, visual safe zones, speech clarity, and public engagement. Private metrics clearly labeled as estimated.
              </p>
            </div>

            <div
              onClick={() => setSubmissionMode("VIDEO_UPLOAD")}
              className={`cursor-pointer rounded-2xl p-5 border transition-all ${
                submissionMode === "VIDEO_UPLOAD"
                  ? "border-violet-600 bg-violet-50/40 shadow-sm ring-1 ring-violet-500"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-100 text-rose-600">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Mode B: Video Upload</h3>
                  <p className="text-xs text-slate-500">Pre-publish draft check</p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-600 leading-relaxed">
                Upload raw MP4/MOV before posting. Detect dead-air pauses, hook drop-off risks, and subtitle collisions in advance.
              </p>
            </div>

            <div
              onClick={() => setSubmissionMode("CONNECTED_ACCOUNT")}
              className={`cursor-pointer rounded-2xl p-5 border transition-all ${
                submissionMode === "CONNECTED_ACCOUNT"
                  ? "border-violet-600 bg-violet-50/40 shadow-sm ring-1 ring-violet-500"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                  <Instagram className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Mode C: Connected Account</h3>
                  <p className="text-xs text-slate-500">Meta Graph API verified</p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-600 leading-relaxed">
                Full access to official reach, private saves, watch ratio, and 30-day account baseline comparisons.
              </p>
            </div>
          </div>

          {/* MODE A: PUBLIC URL INPUT FORM */}
          {submissionMode === "PUBLIC_URL" && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <LinkIcon className="w-4 h-4 text-violet-600" />
                  Analyze Public Reel URL
                </CardTitle>
                <CardDescription className="text-xs">
                  Enter an Instagram Reel URL (e.g. https://www.instagram.com/reel/C8xyzABC123/) or public video link.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmitPublicUrl} className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                      Reel URL <span className="text-rose-500">*</span>
                    </label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="https://www.instagram.com/reel/C8xyzABC123/ or direct video link"
                        value={publicUrl}
                        onChange={(e) => setPublicUrl(e.target.value)}
                        className="flex-1 font-mono text-xs"
                        required
                      />
                      <Button
                        type="submit"
                        disabled={isLoading || !publicUrl.trim()}
                        className="bg-violet-600 hover:bg-violet-700 text-white font-medium shrink-0"
                      >
                        <Sparkles className="w-4 h-4 mr-1.5" />
                        Run Intelligence
                      </Button>
                    </div>
                  </div>

                  {/* Optional self-reported metrics for private Reels */}
                  <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                        <Info className="w-3.5 h-3.5 text-slate-400" />
                        Optional: Manual Metrics (For Non-Scrapable or Private Profiles)
                      </span>
                      <span className="text-[10px] text-slate-400">Overrides automatic scrape</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div>
                        <label className="text-[10px] font-semibold text-slate-500 block mb-1">
                          Current Views
                        </label>
                        <Input
                          type="number"
                          placeholder="e.g. 25000"
                          value={declaredViews}
                          onChange={(e) => setDeclaredViews(e.target.value)}
                          className="h-8 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-semibold text-slate-500 block mb-1">
                          Likes Count
                        </label>
                        <Input
                          type="number"
                          placeholder="e.g. 1800"
                          value={declaredLikes}
                          onChange={(e) => setDeclaredLikes(e.target.value)}
                          className="h-8 text-xs"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Compliance notice */}
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>
                      Public Analysis uses compliant public metadata scraping without requiring login credentials.
                    </span>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* MODE B: VIDEO UPLOAD FORM */}
          {submissionMode === "VIDEO_UPLOAD" && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <UploadCloud className="w-4 h-4 text-rose-500" />
                  Pre-Publish Video File Evaluation
                </CardTitle>
                <CardDescription className="text-xs">
                  Upload an unreleased Reel draft (.mp4, .mov, .webm) up to 100MB to diagnose pacing and safe zones before posting.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept="video/mp4,video/quicktime,video/webm"
                  className="hidden"
                />

                {!selectedFile ? (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/50 p-8 text-center cursor-pointer hover:border-violet-400 hover:bg-violet-50/20 transition-all"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 text-violet-600 mb-3">
                      <FileVideo className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-semibold text-slate-900">
                      Click to select or drag and drop your video file
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Supports MP4, MOV, or WebM (Max 100MB)
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3.5">
                      <div className="flex items-center gap-3">
                        <FileVideo className="w-5 h-5 text-violet-600" />
                        <div>
                          <p className="text-xs font-semibold text-slate-900">{selectedFile.name}</p>
                          <p className="text-[10px] text-slate-500">
                            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedFile(null);
                          setFilePreviewUrl(null);
                        }}
                        className="text-xs text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </Button>
                    </div>

                    {filePreviewUrl && (
                      <div className="relative max-w-xs mx-auto rounded-xl overflow-hidden border border-slate-200 shadow-md bg-black">
                        <video
                          src={filePreviewUrl}
                          controls
                          className="w-full h-auto max-h-72 object-contain"
                        />
                      </div>
                    )}

                    <Button
                      onClick={handleSubmitUpload}
                      disabled={isLoading}
                      className="w-full bg-violet-600 hover:bg-violet-700 text-white font-semibold py-2.5"
                    >
                      <Sparkles className="w-4 h-4 mr-2" />
                      Upload & Analyze Video Intelligence
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* MODE C: CONNECTED ACCOUNT REELS */}
          {submissionMode === "CONNECTED_ACCOUNT" && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Instagram className="w-4 h-4 text-emerald-600" />
                    Select a Reel from {connectedUsername ? `@${connectedUsername}` : "Connected Account"}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Official Meta Graph API authorized metrics (Reach, Saves, Watch Time Ratio).
                  </CardDescription>
                </div>
                <Badge variant="verified">Meta Graph API Active</Badge>
              </CardHeader>
              <CardContent>
                {connectedReels.length === 0 ? (
                  <div className="p-8 text-center">
                    <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-800">
                      No published Reels found on connected account.
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Connect your account in Instagram Sync or test with a public Reel URL.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {connectedReels.map((reel) => (
                      <div
                        key={reel.media_id}
                        className="group flex flex-col justify-between rounded-xl border border-slate-200 bg-white overflow-hidden hover:border-violet-300 hover:shadow-md transition-all"
                      >
                        <div className="relative aspect-[9/16] max-h-48 w-full bg-slate-900 overflow-hidden">
                          <img
                            src={reel.thumbnail_url}
                            alt={reel.title}
                            className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                          <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between text-[11px] text-white font-medium">
                            <span className="flex items-center gap-1">
                              <Eye className="w-3 h-3" />
                              {formatNumber(reel.views)}
                            </span>
                            <span className="flex items-center gap-1">
                              <Heart className="w-3 h-3" />
                              {formatNumber(reel.likes)}
                            </span>
                            <span className="flex items-center gap-1">
                              <MessageCircle className="w-3 h-3" />
                              {reel.comments}
                            </span>
                          </div>
                        </div>

                        <div className="p-3.5 flex-1 flex flex-col justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{reel.title}</h4>
                            <p className="text-[11px] text-slate-500 line-clamp-2 mt-1">{reel.caption}</p>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => handleSubmitConnectedReel(reel)}
                            disabled={isLoading}
                            className="mt-3 w-full bg-violet-50 hover:bg-violet-100 text-violet-700 border border-violet-200 text-xs font-semibold"
                          >
                            <Sparkles className="w-3 h-3 mr-1.5" />
                            Run Deep Analysis
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: COMPREHENSIVE REPORT DASHBOARD                                      */}
      {/* ========================================================================= */}
      {activeTab === "REPORT" && currentReport && (
        <div className="space-y-6">
          {/* Report Top Header Card */}
          <Card className="border-slate-200 shadow-sm overflow-hidden">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between p-6 gap-4 bg-gradient-to-r from-violet-50/40 via-white to-rose-50/30 border-b border-slate-100">
              <div className="flex items-start gap-4">
                <div className="relative h-20 w-14 shrink-0 rounded-lg overflow-hidden bg-slate-900 shadow-md border border-slate-200">
                  <img
                    src={currentReport.thumbnail_url || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&auto=format&fit=crop&q=80"}
                    alt="Thumbnail"
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute bottom-1 right-1 rounded bg-black/70 px-1 py-0.5 text-[9px] font-bold text-white">
                    {Math.round(currentReport.duration_seconds)}s
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900">{currentReport.title}</h2>
                    <Badge
                      variant={currentReport.analysis_mode === "CONNECTED_ACCOUNT" ? "verified" : "sandbox"}
                      className="text-[10px]"
                    >
                      {currentReport.analysis_mode === "CONNECTED_ACCOUNT"
                        ? "Meta Graph API Verified"
                        : "Public Reel Scrape"}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-1 max-w-xl">
                    {currentReport.caption || "No caption text supplied"}
                  </p>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-2">
                    <span>Analyzed: {new Date(currentReport.created_at).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>Duration: {currentReport.duration_seconds.toFixed(1)}s</span>
                    <span>•</span>
                    <span>Aspect Ratio: {currentReport.video_intelligence?.metadata?.aspect_ratio || "9:16"}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleCompareSelect(currentReport.id)}
                  className={`text-xs ${
                    selectedCompareIds.includes(currentReport.id)
                      ? "border-violet-600 text-violet-700 bg-violet-50"
                      : ""
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5 mr-1.5" />
                  {selectedCompareIds.includes(currentReport.id) ? "Selected for Compare" : "Compare Reel"}
                </Button>
                <Button
                  size="sm"
                  onClick={() => setActiveTab("ANALYZE")}
                  className="bg-violet-600 hover:bg-violet-700 text-white text-xs"
                >
                  <Play className="w-3.5 h-3.5 mr-1.5" />
                  New Analysis
                </Button>
              </div>
            </div>

            {/* Public Mode Notice if applicable */}
            {currentReport.analysis_mode !== "CONNECTED_ACCOUNT" && (
              <div className="bg-amber-50/80 border-b border-amber-200 px-6 py-2.5 flex items-center justify-between text-xs text-amber-800">
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    <strong>Public Mode Limitations:</strong> Private metrics (Unique Reach, Attributed Follows, Completion Ratio) are not accessible via public scraping and are marked accordingly.
                  </span>
                </div>
                <button
                  onClick={() => {
                    setSubmissionMode("CONNECTED_ACCOUNT");
                    setActiveTab("ANALYZE");
                  }}
                  className="font-semibold text-amber-900 hover:underline shrink-0 ml-4"
                >
                  Connect Professional Account →
                </button>
              </div>
            )}
          </Card>

          {/* 4 CORE SCORES MATRIX */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Creative Quality Score */}
            <Card className="border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-violet-600" />
              <CardContent className="pt-5">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Creative Quality
                    </span>
                    <div className="flex items-baseline gap-1.5 mt-1">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {(currentReport.scores?.creative_quality?.score ?? currentReport.creative_quality_score ?? 0).toFixed(0)}
                      </span>
                      <span className="text-xs text-slate-400 font-semibold">/100</span>
                    </div>
                  </div>
                  <Badge
                    variant={(currentReport.scores?.creative_quality?.score ?? currentReport.creative_quality_score ?? 0) >= 75 ? "verified" : "warning"}
                    className="text-[10px]"
                  >
                    {currentReport.scores?.creative_quality?.rating || "STRONG"}
                  </Badge>
                </div>

                <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
                  {currentReport.scores?.creative_quality?.components?.slice(0, 3).map((c, i) => (
                    <div key={i} className="flex justify-between text-[11px]">
                      <span className="text-slate-600 truncate max-w-[140px]">{c.name}</span>
                      <span className="font-semibold text-slate-900">{c.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 2. Performance Score */}
            <Card className="border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
              <CardContent className="pt-5">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Performance Score
                    </span>
                    <div className="flex items-baseline gap-1.5 mt-1">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {(currentReport.scores?.performance?.score ?? currentReport.performance_score ?? 0).toFixed(0)}
                      </span>
                      <span className="text-xs text-slate-400 font-semibold">/100</span>
                    </div>
                  </div>
                  <Badge variant="verified" className="text-[10px]">
                    {currentReport.scores?.performance?.rating || "STRONG"}
                  </Badge>
                </div>

                <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
                  {currentReport.scores?.performance?.components?.slice(0, 3).map((c, i) => (
                    <div key={i} className="flex justify-between text-[11px]">
                      <span className="text-slate-600 truncate max-w-[140px]">{c.name}</span>
                      <span className="font-semibold text-slate-900">{c.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 3. Growth Conversion Score */}
            <Card className="border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
              <CardContent className="pt-5">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Growth Conversion
                    </span>
                    <div className="flex items-baseline gap-1.5 mt-1">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {(currentReport.scores?.growth_conversion?.score ?? currentReport.growth_conversion_score ?? 0).toFixed(0)}
                      </span>
                      <span className="text-xs text-slate-400 font-semibold">/100</span>
                    </div>
                  </div>
                  <Badge variant="warning" className="text-[10px]">
                    {currentReport.scores?.growth_conversion?.rating || "MODERATE"}
                  </Badge>
                </div>

                <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
                  {currentReport.scores?.growth_conversion?.components?.slice(0, 3).map((c, i) => (
                    <div key={i} className="flex justify-between text-[11px]">
                      <span className="text-slate-600 truncate max-w-[140px]">{c.name}</span>
                      <span className="font-semibold text-slate-900">{c.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 4. Viral Potential Estimate */}
            <Card className="border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-rose-500" />
              <CardContent className="pt-5">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Viral Potential
                    </span>
                    <div className="flex items-baseline gap-1.5 mt-1">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {(currentReport.scores?.viral_potential?.score ?? currentReport.viral_potential_estimate ?? 0).toFixed(0)}
                      </span>
                      <span className="text-xs text-slate-400 font-semibold">/100</span>
                    </div>
                  </div>
                  <Badge variant="warning" className="text-[10px]">
                    {currentReport.scores?.viral_potential?.rating || "HIGH ESTIMATE"}
                  </Badge>
                </div>

                <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
                  {currentReport.scores?.viral_potential?.components?.slice(0, 3).map((c, i) => (
                    <div key={i} className="flex justify-between text-[11px]">
                      <span className="text-slate-600 truncate max-w-[140px]">{c.name}</span>
                      <span className="font-semibold text-slate-900">{c.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* PERFORMANCE METRICS TRANSPARENT GRID */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center justify-between">
                <span>Calculated Performance Analytics</span>
                <span className="text-xs text-slate-400 font-normal">
                  Hover cards for transparent Numerator & Denominator breakdown
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {Object.entries(currentReport.calculated_metrics || {}).map(([key, item]) => {
                  return (
                    <div
                      key={key}
                      className="group relative rounded-xl border border-slate-200 bg-slate-50/50 p-3 hover:border-violet-300 hover:bg-white hover:shadow-sm transition-all"
                    >
                      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                        <span className="font-semibold truncate">{item.name}</span>
                        {item.benchmark_status && item.benchmark_status !== "N/A" && (
                          <span
                            className={`h-2 w-2 rounded-full ${
                              item.benchmark_status === "ABOVE_AVERAGE"
                                ? "bg-emerald-500"
                                : item.benchmark_status === "AVERAGE"
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                          />
                        )}
                      </div>
                      <div className="text-lg font-extrabold text-slate-900">
                        {item.formatted}
                      </div>
                      <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                        {item.benchmark || item.source}
                      </p>

                      {/* Tooltip Popover on Hover */}
                      <div className="invisible group-hover:visible absolute z-20 left-0 right-0 bottom-full mb-2 p-2.5 rounded-lg bg-slate-900 text-white text-[10px] leading-tight shadow-xl pointer-events-none">
                        <p className="font-bold text-violet-300">{item.name}</p>
                        <p className="mt-1"><strong className="text-slate-300">Formula:</strong> {item.numerator} ÷ {item.denominator}</p>
                        <p className="mt-1 text-slate-400"><strong className="text-slate-300">Limitations:</strong> {item.limitations}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* TIMELINE FINDINGS & VIDEO ANNOTATIONS */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-violet-600" />
                  Timestamped Video Timeline & Creative Findings
                </CardTitle>
                <CardDescription className="text-xs">
                  Moment-by-moment observations on hook delivery, pacing, UI obstruction, and closing CTA.
                </CardDescription>
              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-1">
                {["ALL", "HOOK", "PACING", "VISUAL_CLARITY", "AUDIO_SPEECH", "CTA"].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveTimelineFilter(cat)}
                    className={`rounded-lg px-2.5 py-1 text-[10px] font-semibold transition-all ${
                      activeTimelineFilter === cat
                        ? "bg-violet-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {currentReport.timeline_findings
                ?.filter((f) => activeTimelineFilter === "ALL" || f.category === activeTimelineFilter)
                .map((f: TimelineFinding) => {
                  const severityColor =
                    f.severity === "CRITICAL"
                      ? "border-red-200 bg-red-50/40 text-red-700"
                      : f.severity === "WARNING"
                      ? "border-amber-200 bg-amber-50/40 text-amber-800"
                      : f.severity === "STRENGTH"
                      ? "border-emerald-200 bg-emerald-50/40 text-emerald-800"
                      : "border-blue-200 bg-blue-50/40 text-blue-800";

                  return (
                    <div
                      key={f.id}
                      className="rounded-xl border border-slate-200 bg-white p-4 hover:border-slate-300 transition-all space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-violet-700 bg-violet-100 px-2 py-0.5 rounded">
                            {f.time_range_formatted}
                          </span>
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${severityColor}`}>
                            {f.severity}
                          </span>
                          <span className="text-xs font-semibold text-slate-700">
                            {f.category}
                          </span>
                        </div>

                        {f.is_heuristic_risk && (
                          <span className="text-[10px] text-slate-400 font-medium">
                            Creative Heuristic
                          </span>
                        )}
                      </div>

                      <p className="text-xs font-medium text-slate-900">
                        {f.observation}
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-100">
                        <div>
                          <span className="font-semibold text-slate-700">Evidence: </span>
                          <span className="text-slate-600">{f.evidence}</span>
                        </div>
                        <div>
                          <span className="font-semibold text-slate-700">Proposed Edit: </span>
                          <span className="text-violet-700 font-medium">{f.proposed_edit}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </CardContent>
          </Card>

          {/* PRIORITIZED ACTION PLAN */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Award className="w-4 h-4 text-violet-600" />
                Prioritized Action Plan
              </CardTitle>
              <CardDescription className="text-xs">
                Root-cause diagnosis and actionable engineering steps for your next upload test.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentReport.prioritized_action_plan?.map((plan) => (
                  <div
                    key={plan.priority}
                    className="rounded-xl border border-slate-200 bg-white p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-600 text-white text-[10px] font-extrabold">
                          {plan.priority}
                        </span>
                        <h4 className="text-sm font-bold text-slate-900">{plan.area}</h4>
                      </div>
                      <span className="text-[11px] font-semibold text-violet-700 bg-violet-50 px-2 py-0.5 rounded">
                        Measure: {plan.follow_up_test_metric}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
                        <p className="font-bold text-slate-800 mb-1">What Underperformed</p>
                        <p className="text-slate-600">{plan.what_underperformed}</p>
                        <p className="text-[10px] text-slate-400 mt-2 italic">{plan.why_it_happened}</p>
                      </div>

                      <div className="rounded-lg bg-violet-50/50 p-3 border border-violet-100">
                        <p className="font-bold text-violet-900 mb-1">What to Change</p>
                        <p className="text-violet-800">{plan.what_to_change}</p>
                      </div>

                      <div className="rounded-lg bg-emerald-50/40 p-3 border border-emerald-100">
                        <p className="font-bold text-emerald-900 mb-1">How to Implement</p>
                        <p className="text-emerald-800">{plan.how_to_implement}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* CREATIVE ALTERNATIVES STUDIO */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-4">
              <div>
                <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-violet-600" />
                  Creative Experiments Studio
                </CardTitle>
                <CardDescription className="text-xs">
                  Generate alternative hooks, thumbnail concepts, caption variations, and shot-by-shot edits.
                </CardDescription>
              </div>

              {/* Sub-tab Switcher */}
              <div className="flex gap-1 rounded-lg bg-slate-100 p-1 border border-slate-200">
                {[
                  { key: "HOOKS", label: "Hooks" },
                  { key: "THUMBNAILS", label: "Thumbnails" },
                  { key: "CAPTIONS", label: "Captions" },
                  { key: "CTA", label: "CTAs" },
                  { key: "SCRIPT", label: "Revised Script" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveExperimentTab(t.key as any)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-all ${
                      activeExperimentTab === t.key
                        ? "bg-white text-violet-700 shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {/* HOOKS */}
              {activeExperimentTab === "HOOKS" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentReport.creative_alternatives?.alternative_hooks?.map((h, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2 hover:border-violet-300 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-violet-700 bg-violet-50 px-2 py-0.5 rounded">
                          {h.framework}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(h.hook_text, `hook_${i}`)}
                          className="h-7 px-2 text-xs text-slate-500 hover:text-slate-900"
                        >
                          {copiedKey === `hook_${i}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </Button>
                      </div>
                      <p className="text-xs font-semibold text-slate-900">"{h.hook_text}"</p>
                      <p className="text-[11px] text-slate-500 leading-tight">{h.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* THUMBNAILS */}
              {activeExperimentTab === "THUMBNAILS" && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {currentReport.creative_alternatives?.thumbnail_concepts?.map((t, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-slate-200 bg-white p-4 space-y-2.5 hover:border-violet-300 transition-all"
                    >
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Concept {i + 1}
                      </span>
                      <div className="rounded-lg bg-slate-900 text-amber-400 p-2.5 text-center font-extrabold text-xs tracking-tight shadow-sm">
                        {t.overlay_text}
                      </div>
                      <p className="text-xs text-slate-700 font-medium">{t.visual_direction}</p>
                      <p className="text-[11px] text-slate-400">
                        <strong className="text-slate-600">Focal Point:</strong> {t.focal_point}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* CAPTIONS */}
              {activeExperimentTab === "CAPTIONS" && (
                <div className="space-y-3">
                  {currentReport.creative_alternatives?.caption_suggestions?.map((c, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 hover:border-violet-300 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">{c.variation_name}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(`${c.text}\n\n${c.suggested_hashtags}`, `cap_${i}`)}
                          className="h-7 px-2 text-xs text-slate-500"
                        >
                          {copiedKey === `cap_${i}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </Button>
                      </div>
                      <p className="text-xs text-slate-700 whitespace-pre-line leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100 font-sans">
                        {c.text}
                      </p>
                      <p className="text-[11px] text-violet-600 font-medium">{c.suggested_hashtags}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* CTA */}
              {activeExperimentTab === "CTA" && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {currentReport.creative_alternatives?.cta_variations?.map((cta, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">{cta.type}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(cta.cta_text, `cta_${i}`)}
                          className="h-6 px-1.5"
                        >
                          {copiedKey === `cta_${i}` ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </Button>
                      </div>
                      <p className="text-xs font-semibold text-slate-900">"{cta.cta_text}"</p>
                    </div>
                  ))}
                </div>
              )}

              {/* REVISED SCRIPT */}
              {activeExperimentTab === "SCRIPT" && currentReport.creative_alternatives?.revised_script && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
                    <div className="rounded-lg bg-violet-50 p-3 border border-violet-100">
                      <span className="font-bold text-violet-900 block mb-1">Hook (0-3s)</span>
                      <p className="text-violet-800">{currentReport.creative_alternatives.revised_script.hook}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
                      <span className="font-bold text-slate-800 block mb-1">Body Pacing</span>
                      <p className="text-slate-600">{currentReport.creative_alternatives.revised_script.body}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
                      <span className="font-bold text-slate-800 block mb-1">Payoff</span>
                      <p className="text-slate-600">{currentReport.creative_alternatives.revised_script.payoff}</p>
                    </div>
                    <div className="rounded-lg bg-emerald-50 p-3 border border-emerald-100">
                      <span className="font-bold text-emerald-900 block mb-1">Closing CTA</span>
                      <p className="text-emerald-800">{currentReport.creative_alternatives.revised_script.cta}</p>
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-100 p-3 text-xs text-slate-600">
                    <strong className="text-slate-800">Shot-by-Shot Editing Notes: </strong>
                    {currentReport.creative_alternatives.revised_script.shot_notes}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: HISTORY & ARCHIVE                                                   */}
      {/* ========================================================================= */}
      {activeTab === "HISTORY" && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <CardTitle className="text-base font-bold text-slate-900">
                Reel Analysis Archive
              </CardTitle>
              <CardDescription className="text-xs">
                Browse historical reports, review score trajectories, or select Reels for side-by-side comparison.
              </CardDescription>
            </div>

            {selectedCompareIds.length >= 2 && (
              <Button
                onClick={handleCompareSubmit}
                className="bg-violet-600 hover:bg-violet-700 text-white text-xs"
              >
                <Sliders className="w-3.5 h-3.5 mr-1.5" />
                Compare Selected ({selectedCompareIds.length})
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {reportsList.length === 0 ? (
              <div className="p-12 text-center">
                <Film className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <h3 className="text-sm font-semibold text-slate-800">No Reel reports yet</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  Submit a public Reel URL, upload a video file, or select a published post from your connected account.
                </p>
                <Button
                  size="sm"
                  onClick={() => setActiveTab("ANALYZE")}
                  className="mt-4 bg-violet-600 text-white text-xs"
                >
                  Analyze First Reel
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white">
                {reportsList.map((rep) => {
                  const isSelected = selectedCompareIds.includes(rep.id);
                  return (
                    <div
                      key={rep.id}
                      className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-4 hover:bg-slate-50/70 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleCompareSelect(rep.id)}
                          className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
                        />
                        <div className="relative h-14 w-10 shrink-0 rounded overflow-hidden bg-slate-900 border border-slate-200">
                          <img
                            src={rep.thumbnail_url || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&auto=format&fit=crop&q=80"}
                            alt={rep.title}
                            className="h-full w-full object-cover"
                          />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{rep.title}</h4>
                          <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-0.5">
                            <span>{new Date(rep.created_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <Badge variant={rep.analysis_mode === "CONNECTED_ACCOUNT" ? "verified" : "sandbox"} className="text-[9px] py-0">
                              {rep.analysis_mode === "CONNECTED_ACCOUNT" ? "Meta API" : "Public URL"}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-xs">
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block">Creative</span>
                          <span className="font-extrabold text-slate-900">{rep.creative_quality_score.toFixed(0)}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block">Performance</span>
                          <span className="font-extrabold text-emerald-600">{rep.performance_score.toFixed(0)}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block">Viral Est.</span>
                          <span className="font-extrabold text-rose-600">{rep.viral_potential_estimate.toFixed(0)}</span>
                        </div>

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => loadReport(rep.id, true)}
                          className="text-xs font-semibold"
                        >
                          View Report
                          <ChevronRight className="w-3.5 h-3.5 ml-1" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: REEL COMPARISON VIEW                                                */}
      {/* ========================================================================= */}
      {activeTab === "COMPARE" && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-violet-600" />
              Side-by-Side Reel Comparison Matrix
            </CardTitle>
            <CardDescription className="text-xs">
              Compare creative quality, engagement velocity, and algorithmic potential across multiple Reels.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!comparisonResult ? (
              <div className="p-8 text-center">
                <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-800">
                  Select at least 2 Reels from the Archive to generate a comparison matrix.
                </p>
                <Button
                  size="sm"
                  onClick={() => setActiveTab("HISTORY")}
                  className="mt-3 bg-violet-600 text-white text-xs"
                >
                  Go to Archive & Select
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* AI Comparative Takeaways Banner */}
                <div className="rounded-xl border border-violet-200 bg-violet-50/60 p-4 space-y-2">
                  <span className="text-xs font-bold text-violet-900 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                    Comparative AI Takeaways
                  </span>
                  <ul className="list-disc pl-5 text-xs text-violet-950 space-y-1">
                    {comparisonResult.comparative_takeaways?.map((t, idx) => (
                      <li key={idx}>{t}</li>
                    ))}
                  </ul>
                </div>

                {/* Comparison Columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {comparisonResult.reports?.map((rep) => {
                    const isWinner = rep.id === comparisonResult.winner_id;
                    return (
                      <div
                        key={rep.id}
                        className={`rounded-2xl border p-5 bg-white relative transition-all ${
                          isWinner ? "border-violet-600 shadow-md ring-1 ring-violet-500" : "border-slate-200 shadow-sm"
                        }`}
                      >
                        {isWinner && (
                          <div className="absolute top-3 right-3">
                            <Badge variant="verified" className="bg-violet-600 text-white border-0">
                              Top Performer
                            </Badge>
                          </div>
                        )}

                        <div className="flex items-center gap-3">
                          <div className="relative h-14 w-10 shrink-0 rounded overflow-hidden bg-slate-900">
                            <img
                              src={rep.thumbnail_url || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&auto=format&fit=crop&q=80"}
                              alt={rep.title}
                              className="h-full w-full object-cover"
                            />
                          </div>
                          <div>
                            <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{rep.title}</h4>
                            <span className="text-[10px] text-slate-400">
                              Duration: {rep.duration_seconds.toFixed(0)}s
                            </span>
                          </div>
                        </div>

                        {/* Scores Block */}
                        <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500 font-medium">Creative Quality:</span>
                            <span className="font-extrabold text-slate-900">{(rep.scores?.creative_quality?.score ?? rep.creative_quality_score ?? 0).toFixed(0)}</span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500 font-medium">Performance Score:</span>
                            <span className="font-extrabold text-emerald-600">{(rep.scores?.performance?.score ?? rep.performance_score ?? 0).toFixed(0)}</span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500 font-medium">Growth Conversion:</span>
                            <span className="font-extrabold text-amber-600">{(rep.scores?.growth_conversion?.score ?? rep.growth_conversion_score ?? 0).toFixed(0)}</span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500 font-medium">Viral Potential:</span>
                            <span className="font-extrabold text-rose-600">{(rep.scores?.viral_potential?.score ?? rep.viral_potential_estimate ?? 0).toFixed(0)}</span>
                          </div>
                        </div>

                        <Button
                          size="sm"
                          onClick={() => {
                            setCurrentReport(rep);
                            setActiveTab("REPORT");
                          }}
                          className="mt-4 w-full text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800"
                        >
                          Inspect Full Report
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
