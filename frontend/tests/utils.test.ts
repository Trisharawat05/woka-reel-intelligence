import test from "node:test";
import assert from "node:assert/strict";
import { formatNumber, formatCurrency, cn } from "../src/lib/utils.ts";

test("formatNumber formats millions correctly", () => {
  assert.equal(formatNumber(1500000), "1.5M");
  assert.equal(formatNumber(1000000), "1.0M");
});

test("formatNumber formats thousands correctly", () => {
  assert.equal(formatNumber(48500), "48.5k");
  assert.equal(formatNumber(1200), "1.2k");
});

test("formatNumber formats small numbers correctly", () => {
  assert.equal(formatNumber(950), "950");
  assert.equal(formatNumber(0), "0");
});

test("formatCurrency formats USD correctly", () => {
  const formatted = formatCurrency(1250);
  assert.match(formatted, /\$1,250/);
});

test("cn utility merges class names correctly", () => {
  const merged = cn("btn", "btn-primary", { "is-active": true, "is-disabled": false });
  assert.match(merged, /btn/);
  assert.match(merged, /btn-primary/);
  assert.match(merged, /is-active/);
  assert.doesNotMatch(merged, /is-disabled/);
});
