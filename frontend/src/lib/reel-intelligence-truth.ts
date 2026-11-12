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
  return { label: "Public URL Mode", variant: "sandbox" };
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
