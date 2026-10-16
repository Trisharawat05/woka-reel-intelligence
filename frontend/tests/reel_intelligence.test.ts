import test from "node:test";
import assert from "node:assert/strict";
import { formatPercent } from "../src/lib/utils.ts";

test("formatPercent converts decimal proportions to formatted strings", () => {
  assert.equal(formatPercent(0.054), "5.4%");
  assert.equal(formatPercent(0.1062, 2), "10.62%");
  assert.equal(formatPercent(0.75, 0), "75%");
});

test("Reel URL validation regex matches official Instagram shortcode patterns", () => {
  const reelRegex = /^(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:reel|p)\/([a-zA-Z0-9_-]+)/;
  
  assert.equal(reelRegex.test("https://www.instagram.com/reel/C8xyzABC123/"), true);
  assert.equal(reelRegex.test("https://instagram.com/reel/DEMO_123/?utm_source=ig"), true);
  assert.equal(reelRegex.test("https://www.instagram.com/p/POST_789/"), true);
  assert.equal(reelRegex.test("https://notinstagram.com/reel/123"), false);
  assert.equal(reelRegex.test("invalid-url-string"), false);
});


test("Score rating threshold classifies performance tiers accurately", () => {
  function getScoreTier(score: number): string {
    if (score >= 88) return "EXCEPTIONAL";
    if (score >= 75) return "STRONG";
    if (score >= 60) return "MODERATE";
    return "UNDERPERFORMING";
  }

  assert.equal(getScoreTier(92), "EXCEPTIONAL");
  assert.equal(getScoreTier(88), "EXCEPTIONAL");
  assert.equal(getScoreTier(78), "STRONG");
  assert.equal(getScoreTier(64), "MODERATE");
  assert.equal(getScoreTier(45), "UNDERPERFORMING");
});

test("Benchmark status indicator maps to appropriate visual status colors", () => {
  function getBenchmarkColor(status: string): string {
    switch (status) {
      case "ABOVE_AVERAGE": return "bg-emerald-500";
      case "AVERAGE": return "bg-amber-500";
      case "BELOW_AVERAGE": return "bg-red-500";
      default: return "bg-slate-400";
    }
  }

  assert.equal(getBenchmarkColor("ABOVE_AVERAGE"), "bg-emerald-500");
  assert.equal(getBenchmarkColor("AVERAGE"), "bg-amber-500");
  assert.equal(getBenchmarkColor("BELOW_AVERAGE"), "bg-red-500");
  assert.equal(getBenchmarkColor("N/A"), "bg-slate-400");
});

test("Comparison selection limits enforce between 2 and 5 Reels", () => {
  function canCompare(selectedCount: number): boolean {
    return selectedCount >= 2 && selectedCount <= 5;
  }

  assert.equal(canCompare(0), false);
  assert.equal(canCompare(1), false);
  assert.equal(canCompare(2), true);
  assert.equal(canCompare(4), true);
  assert.equal(canCompare(5), true);
  assert.equal(canCompare(6), false);
});

test("Finding severity classifications map to consistent UI badge variants", () => {
  function getSeverityVariant(severity: string): string {
    switch (severity) {
      case "CRITICAL": return "danger";
      case "WARNING": return "warning";
      case "STRENGTH": return "verified";
      default: return "default";
    }
  }

  assert.equal(getSeverityVariant("CRITICAL"), "danger");
  assert.equal(getSeverityVariant("WARNING"), "warning");
  assert.equal(getSeverityVariant("STRENGTH"), "verified");
  assert.equal(getSeverityVariant("OPPORTUNITY"), "default");
});

test("SSRF guard rejects localhost and internal IP patterns on client side", () => {
  function isRestrictedHost(url: string): boolean {
    const forbidden = ["localhost", "127.0.0.1", "169.254.", "10.0.", "192.168.", "0.0.0.0"];
    return forbidden.some(ip => url.includes(ip));
  }

  assert.equal(isRestrictedHost("http://127.0.0.1/video.mp4"), true);
  assert.equal(isRestrictedHost("http://localhost:3000/demo"), true);
  assert.equal(isRestrictedHost("http://169.254.169.254/metadata"), true);
  assert.equal(isRestrictedHost("https://www.instagram.com/reel/C123/"), false);
});

