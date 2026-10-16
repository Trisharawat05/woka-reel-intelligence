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
