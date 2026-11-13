import type { MetricItem, ReelReport } from "../types/index.ts";

export function isReportSimulated(report: Pick<ReelReport, "provenance">): boolean {
  return Boolean(report.provenance?.is_simulated || report.provenance?.metric_source_mode === "SANDBOX_SIMULATION");
}

export function getReportSourceBadge(report: Pick<ReelReport, "analysis_mode" | "provenance">): {
  label: string;
  variant: "verified" | "sandbox" | "secondary";
} {
  if (isReportSimulated(report)) {
    return { label: "Sandbox Simulated (Demo Data)", variant: "sandbox" };
  }
  if (report.analysis_mode === "CONNECTED_ACCOUNT") {
    return { label: "Meta Graph API Connected", variant: "verified" };
  }
  if (report.analysis_mode === "VIDEO_UPLOAD") {
    return { label: "Local Video Draft", variant: "secondary" };
  }
  return { label: "Universal Video URL Analysis", variant: "sandbox" };
}

export function getMetricCategoryBadge(item: Pick<MetricItem, "category" | "value" | "is_simulated">): {
  label: string;
  toneClass: string;
} {
  if (item.is_simulated || item.category === "SIMULATED") {
    return { label: "Simulated", toneClass: "bg-amber-100 text-amber-900 border-amber-300" };
  }
  if (item.category === "MEASURED") {
    return { label: "Measured", toneClass: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  }
  if (item.category === "CALCULATED") {
    return { label: "Calculated", toneClass: "bg-violet-50 text-violet-700 border-violet-200" };
  }
  if (item.category === "ESTIMATED") {
    return { label: "AI Estimate", toneClass: "bg-sky-50 text-sky-700 border-sky-200" };
  }
  return { label: "Unavailable", toneClass: "bg-slate-100 text-slate-600 border-slate-200" };
}

export function formatReportDurationLabel(report: Pick<ReelReport, "duration_seconds" | "provenance" | "video_intelligence">): string {
  const measured = Boolean(report.provenance?.duration_measured ?? report.video_intelligence?.metadata?.duration_measured);
  if (measured && report.duration_seconds > 0) {
    return `${report.duration_seconds.toFixed(1)}s`;
  }
  if (isReportSimulated(report) && report.duration_seconds > 0) {
    return `~${report.duration_seconds.toFixed(0)}s (Simulated)`;
  }
  return "Unavailable";
}

export interface VideoExtractionStatusResult {
  status: "DECODED" | "FAILED" | "SIMULATED" | "UNAVAILABLE";
  message: string;
  canRetry: boolean;
}

export function getVideoExtractionStatus(
  report: Pick<ReelReport, "video_intelligence" | "provenance" | "analysis_mode">
): VideoExtractionStatusResult {
  if (isReportSimulated(report)) {
    return {
      status: "SIMULATED",
      message: "Synthetic sandbox metrics rendered for demonstration. Pixel-level decoding was not performed on a real video stream.",
      canRetry: false,
    };
  }

  const vi = report.video_intelligence;
  if (!vi) {
    return {
      status: "UNAVAILABLE",
      message: "No video stream data available for this report.",
      canRetry: true,
    };
  }

  const isStreamAnalyzed = Boolean(
    vi.video_stream_analyzed ??
    vi.metadata?.video_stream_analyzed ??
    report.provenance?.video_stream_analyzed
  );

  if (isStreamAnalyzed) {
    const meta = vi.metadata || {};
    const width = meta.width ?? meta.resolution_width ?? 0;
    const height = meta.height ?? meta.resolution_height ?? 0;
    const fps = meta.fps ? Number(meta.fps).toFixed(1) : "0.0";
    const dur = meta.duration_seconds ? Number(meta.duration_seconds).toFixed(1) : "0.0";
    const cuts = vi.visual_metrics?.scene_cuts_count ?? vi.visual_pacing?.cuts_detected ?? 0;
    return {
      status: "DECODED",
      message: `Video stream successfully decoded locally (${width}x${height} @ ${fps} fps, ${dur}s, ${cuts} scene cuts detected).`,
      canRetry: false,
    };
  }

  // If stream was not analyzed
  const reason =
    vi.limitation_reason ||
    vi.metadata?.limitation ||
    report.provenance?.video_limitation ||
    (report.analysis_mode === "PUBLIC_URL"
      ? "Public Instagram Reel page URLs require authentication to access the underlying video stream. Raw video pixels could not be retrieved directly."
      : "Video stream could not be decoded.");

  return {
    status: "FAILED",
    message: reason,
    canRetry: true,
  };
}

