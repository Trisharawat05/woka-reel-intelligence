import test from "node:test";
import assert from "node:assert/strict";
import {
  getVideoExtractionStatus,
  formatReportDurationLabel,
} from "../src/lib/reel-intelligence-truth.ts";

test("getVideoExtractionStatus identifies DECODED video with metadata and cuts", () => {
  const decodedReport = {
    analysis_mode: "VIDEO_UPLOAD" as const,
    video_intelligence: {
      video_stream_analyzed: true,
      metadata: {
        width: 1080,
        height: 1920,
        fps: 30.0,
        duration_seconds: 14.5,
        aspect_ratio: "9:16",
        duration_measured: true,
      },
      visual_metrics: {
        scene_cuts_count: 5,
        average_scene_duration_seconds: 2.9,
      },
      audio_metrics: {
        data_available: true,
        speech_detected: true,
      },
    },
    provenance: {
      is_simulated: false,
    },
  };

  const status = getVideoExtractionStatus(decodedReport);
  assert.equal(status.status, "DECODED");
  assert.equal(status.canRetry, false);
  assert.match(status.message, /1080x1920/);
  assert.match(status.message, /30\.0 fps/);
  assert.match(status.message, /14\.5s/);
  assert.match(status.message, /5 scene cuts/);
});

test("getVideoExtractionStatus identifies FAILED public Reel extraction with actionable guidance", () => {
  const failedPublicReport = {
    analysis_mode: "PUBLIC_URL" as const,
    video_intelligence: {
      video_stream_analyzed: false,
      limitation_reason:
        "Instagram Reel page URLs do not provide direct video stream access without authentication.",
      video_source: "INSTAGRAM_PAGE_UNSUPPORTED",
    },
    provenance: {
      is_simulated: false,
      video_limitation:
        "Instagram Reel page URLs do not provide direct video stream access without authentication.",
    },
  };

  const status = getVideoExtractionStatus(failedPublicReport);
  assert.equal(status.status, "FAILED");
  assert.equal(status.canRetry, true);
  assert.match(status.message, /Instagram Reel page URLs/i);
});

test("getVideoExtractionStatus identifies SIMULATED reports and prohibits false retry", () => {
  const simulatedReport = {
    analysis_mode: "PUBLIC_URL" as const,
    video_intelligence: {
      video_stream_analyzed: false,
    },
    provenance: {
      is_simulated: true,
      metric_source_mode: "SANDBOX_SIMULATION",
    },
  };

  const status = getVideoExtractionStatus(simulatedReport);
  assert.equal(status.status, "SIMULATED");
  assert.equal(status.canRetry, false);
  assert.match(status.message, /Synthetic sandbox metrics/i);
});

test("getVideoExtractionStatus handles missing video_intelligence gracefully as UNAVAILABLE", () => {
  const missingViReport = {
    analysis_mode: "PUBLIC_URL" as const,
    video_intelligence: undefined as any,
    provenance: {
      is_simulated: false,
    },
  };

  const status = getVideoExtractionStatus(missingViReport);
  assert.equal(status.status, "UNAVAILABLE");
  assert.equal(status.canRetry, true);
});

test("formatReportDurationLabel accurately reflects measured, simulated, and unavailable durations", () => {
  // Measured duration
  assert.equal(
    formatReportDurationLabel({
      duration_seconds: 22.8,
      provenance: { duration_measured: true, is_simulated: false },
      video_intelligence: { metadata: { duration_measured: true } },
    }),
    "22.8s"
  );

  // Simulated duration
  assert.equal(
    formatReportDurationLabel({
      duration_seconds: 30,
      provenance: { duration_measured: false, is_simulated: true },
      video_intelligence: { metadata: { duration_measured: false } },
    }),
    "~30s (Simulated)"
  );

  // Unavailable duration
  assert.equal(
    formatReportDurationLabel({
      duration_seconds: 0,
      provenance: { duration_measured: false, is_simulated: false },
      video_intelligence: { metadata: { duration_measured: false } },
    }),
    "Unavailable"
  );
});

test("getVideoExtractionStatus handles public direct MP4 with nested metadata cleanly as DECODED", () => {
  const publicDirectReport = {
    analysis_mode: "PUBLIC_URL" as const,
    video_intelligence: {
      metadata: {
        width: 1080,
        height: 1920,
        fps: 30.0,
        duration_seconds: 15.0,
        aspect_ratio: "9:16",
        duration_measured: true,
        video_stream_analyzed: true,
      },
      visual_pacing: {
        cuts_detected: 4,
      },
    },
    provenance: {
      is_simulated: false,
      video_stream_analyzed: true,
    },
  };

  const status = getVideoExtractionStatus(publicDirectReport);
  assert.equal(status.status, "DECODED");
  assert.equal(status.canRetry, false);
  assert.match(status.message, /1080x1920/);
  assert.match(status.message, /30\.0 fps/);
  assert.match(status.message, /15\.0s/);
  assert.match(status.message, /4 scene cuts/);
});
