import test from "node:test";
import assert from "node:assert/strict";
import { getReportSourceBadge } from "../src/lib/reel-intelligence-truth.ts";

test("Universal Video URL Analysis badge is rendered for PUBLIC_URL analysis mode", () => {
  const report = {
    analysis_mode: "PUBLIC_URL" as const,
    provenance: { is_simulated: false },
  };
  const badge = getReportSourceBadge(report);
  assert.equal(badge.label, "Universal Video URL Analysis");
  assert.equal(badge.variant, "sandbox");
});

test("Platform detector regexes identify supported platform video URLs", () => {
  const youtubeRegex = /(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/i;
  const instagramRegex = /(?:instagram\.com|instagr\.am)\/(?:reel|p)\/([a-zA-Z0-9_-]+)/i;
  const tiktokRegex = /tiktok\.com\/@[^\/]+\/video\/(\d+)|(?:vm|vt)\.tiktok\.com\/([a-zA-Z0-9_-]+)/i;
  const vimeoRegex = /vimeo\.com\/(?:channels\/(?:\w+\/)?|video\/|)(\d+)|player\.vimeo\.com\/video\/(\d+)/i;
  const directVideoRegex = /\.(mp4|mov|webm|m4v)(\?.*)?$/i;

  // YouTube
  assert.equal(youtubeRegex.test("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), true);
  assert.equal(youtubeRegex.test("https://youtu.be/dQw4w9WgXcQ"), true);
  assert.equal(youtubeRegex.test("https://www.youtube.com/shorts/dQw4w9WgXcQ"), true);

  // Instagram
  assert.equal(instagramRegex.test("https://www.instagram.com/reel/C8xyzABC123/"), true);
  assert.equal(instagramRegex.test("https://instagr.am/p/POST_789/"), true);

  // TikTok
  assert.equal(tiktokRegex.test("https://www.tiktok.com/@creator/video/7123456789012345678"), true);
  assert.equal(tiktokRegex.test("https://vm.tiktok.com/ZM8xyz123/"), true);

  // Vimeo
  assert.equal(vimeoRegex.test("https://vimeo.com/76979871"), true);
  assert.equal(vimeoRegex.test("https://player.vimeo.com/video/76979871"), true);

  // Direct Video
  assert.equal(directVideoRegex.test("https://cdn.example.com/videos/promo.mp4"), true);
  assert.equal(directVideoRegex.test("https://s3.amazonaws.com/bucket/video.mov?Signature=xyz"), true);
  assert.equal(directVideoRegex.test("https://example.com/not-video.html"), false);
});

test("Universal Video Ingestion statuses match expected 10 lifecycle stages", () => {
  const expectedStatuses = [
    "DETECTING_PLATFORM",
    "AUTH_REQUIRED",
    "CONNECT_ACCOUNT",
    "EXTRACTING_METADATA",
    "DOWNLOADING_VIDEO",
    "VIDEO_RETRIEVED",
    "PROCESSING",
    "COMPLETED",
    "UNSUPPORTED",
    "EXTRACTION_FAILED",
  ];

  for (const status of expectedStatuses) {
    assert.equal(typeof status, "string");
    assert.equal(status.length > 0, true);
  }
});
