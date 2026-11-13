import test from "node:test";
import assert from "node:assert/strict";
import {
  formatReportDurationLabel,
  getMetricCategoryBadge,
  getReportSourceBadge,
  isReportSimulated,
} from "../src/lib/reel-intelligence-truth.ts";

test("sandbox simulated connected reports never claim Meta Graph API verification", () => {
  const sandboxReport = {
    analysis_mode: "CONNECTED_ACCOUNT" as const,
    provenance: { is_simulated: true, metric_source_mode: "SANDBOX_SIMULATION" },
  };
  assert.equal(isReportSimulated(sandboxReport), true);
  const badge = getReportSourceBadge(sandboxReport);
  assert.equal(badge.variant, "sandbox");
  assert.match(badge.label, /Sandbox Simulated/i);
  assert.doesNotMatch(badge.label, /Verified/i);

  const liveReport = {
    analysis_mode: "CONNECTED_ACCOUNT" as const,
    provenance: { is_simulated: false, metric_source_mode: "META_GRAPH_API" },
  };
  assert.equal(isReportSimulated(liveReport), false);
  assert.equal(getReportSourceBadge(liveReport).variant, "verified");
});

test("metric category badges clearly separate Measured, Calculated, Simulated, AI Estimate, and Unavailable", () => {
  assert.equal(getMetricCategoryBadge({ category: "MEASURED", value: 120, is_simulated: false }).label, "Measured");
  assert.equal(getMetricCategoryBadge({ category: "CALCULATED", value: 0.05, is_simulated: false }).label, "Calculated");
  assert.equal(getMetricCategoryBadge({ category: "SIMULATED", value: 28450, is_simulated: true }).label, "Simulated");
  assert.equal(getMetricCategoryBadge({ category: "ESTIMATED", value: 75, is_simulated: false }).label, "AI Estimate");
  assert.equal(getMetricCategoryBadge({ category: "UNAVAILABLE", value: null, is_simulated: false }).label, "Unavailable");
});

test("formatReportDurationLabel reports Unavailable when stream duration is unmeasured", () => {
  assert.equal(
    formatReportDurationLabel({
      duration_seconds: 0,
      provenance: { duration_measured: false, is_simulated: false },
      video_intelligence: { metadata: { duration_measured: false } },
    }),
    "Unavailable"
  );
  assert.equal(
    formatReportDurationLabel({
      duration_seconds: 18.4,
      provenance: { duration_measured: true, is_simulated: false },
      video_intelligence: { metadata: { duration_measured: true } },
    }),
    "18.4s"
  );
});

test("universal video URL report badge displays Universal Video URL Analysis", () => {
  const publicVideoReport = {
    analysis_mode: "PUBLIC_URL" as const,
    provenance: { is_simulated: false },
  };
  const badge = getReportSourceBadge(publicVideoReport);
  assert.equal(badge.label, "Universal Video URL Analysis");
  assert.equal(badge.variant, "sandbox");
});

test("Mode A metric items distinguish measured values from unavailable explanations", () => {
  const measuredMetric = {
    name: "Likes",
    value: 1840,
    formatted: "1,840",
    numerator: "Total like reactions",
    denominator: "None",
    time_window: "Lifetime",
    source: "Public Video Metadata (Likes)",
    category: "MEASURED",
    benchmark_status: "N/A" as const,
    limitations: "Reported from public video page metadata.",
  };
  assert.equal(getMetricCategoryBadge(measuredMetric).label, "Measured");

  const calculatedMetric = {
    name: "Like Rate (Views)",
    value: 0.0647,
    formatted: "6.47%",
    numerator: "Likes (1,840)",
    denominator: "Total Views (28,450)",
    time_window: "Lifetime",
    source: "Calculated Ratio (Likes / Views)",
    category: "CALCULATED",
    benchmark_status: "AVERAGE" as const,
    limitations: "Does not separate repeat plays from unique viewers.",
  };
  assert.equal(getMetricCategoryBadge(calculatedMetric).label, "Calculated");

  const privateMetric = {
    name: "Unique Reach",
    value: null,
    formatted: "N/A",
    numerator: "Count of unique accounts",
    denominator: "None",
    time_window: "Lifetime",
    source: "Requires connected Instagram account",
    unavailable_reason: "Requires connected Instagram account",
    category: "UNAVAILABLE",
    benchmark_status: "N/A" as const,
    limitations: "Unique reach requires an authenticated Meta Graph API connection.",
  };
  assert.equal(getMetricCategoryBadge(privateMetric).label, "Unavailable");
  assert.equal(privateMetric.unavailable_reason, "Requires connected Instagram account");

  const insufficientDataMetric = {
    name: "Like Rate (Views)",
    value: null,
    formatted: "N/A",
    numerator: "Likes",
    denominator: "Total Views",
    time_window: "Lifetime",
    source: "Insufficient data to calculate",
    unavailable_reason: "Insufficient data to calculate",
    category: "UNAVAILABLE",
    benchmark_status: "N/A" as const,
    limitations: "Requires both Likes and Views counts.",
  };
  assert.equal(getMetricCategoryBadge(insufficientDataMetric).label, "Unavailable");
  assert.equal(insufficientDataMetric.unavailable_reason, "Insufficient data to calculate");
});
