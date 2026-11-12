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
