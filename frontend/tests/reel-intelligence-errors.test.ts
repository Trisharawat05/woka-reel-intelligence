import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_FRIENDLY_ANALYSIS_ERROR,
  toFriendlyAnalysisError,
} from "../src/lib/reel-intelligence-errors.ts";

test("toFriendlyAnalysisError masks raw psycopg2 UniqueViolation SQL exceptions", () => {
  const rawPostgresErr =
    '(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "reel_reports_job_id_key" ' +
    'DETAIL: Key (job_id)=(abc-123) already exists. [SQL: INSERT INTO reel_reports (id, workspace_id, job_id) VALUES (%s, %s, %s)]';

  const result = toFriendlyAnalysisError(rawPostgresErr);
  assert.equal(result, DEFAULT_FRIENDLY_ANALYSIS_ERROR);
  assert.doesNotMatch(result, /psycopg2|reel_reports|INSERT INTO|SQL/i);
});

test("toFriendlyAnalysisError masks sqlite3 IntegrityError and tracebacks", () => {
  const rawSqliteErr =
    "(sqlite3.IntegrityError) UNIQUE constraint failed: reel_reports.job_id [SQL: INSERT INTO reel_reports ...]";
  assert.equal(toFriendlyAnalysisError(rawSqliteErr, "Custom fallback"), "Custom fallback");

  const tracebackErr = "Traceback (most recent call last): File ...";
  assert.equal(toFriendlyAnalysisError(tracebackErr, "Safe message"), "Safe message");
});

test("toFriendlyAnalysisError preserves clean user-facing domain messages", () => {
  const quotaMsg =
    "Monthly Reel AI analysis quota exceeded for your workspace plan. Please upgrade your subscription.";
  assert.equal(toFriendlyAnalysisError(quotaMsg), quotaMsg);
  assert.equal(toFriendlyAnalysisError(null, "Fallback error"), "Fallback error");
  assert.equal(toFriendlyAnalysisError("   ", "Fallback error"), "Fallback error");
});
