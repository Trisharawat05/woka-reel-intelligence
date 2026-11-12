const INTERNAL_SQL_OR_TRACE_PATTERNS = [
  "psycopg2",
  "sqlite3",
  "sqlalchemy",
  "uniqueviolation",
  "integrityerror",
  "operationalerror",
  "duplicate key value",
  "violates unique constraint",
  "unique constraint failed",
  "[sql:",
  "[parameters:",
  "traceback",
  "select ",
  "insert into ",
  "update ",
  "delete from ",
  "postgresql://",
  "sqlite:///",
];

export const DEFAULT_FRIENDLY_ANALYSIS_ERROR =
  "Reel analysis could not be completed right now. Please click Retry Analysis or try again.";

export function toFriendlyAnalysisError(
  rawMessage?: string | null,
  fallback: string = DEFAULT_FRIENDLY_ANALYSIS_ERROR
): string {
  const cleaned = typeof rawMessage === "string" ? rawMessage.trim() : "";
  if (!cleaned) {
    return fallback;
  }

  const lowered = cleaned.toLowerCase();
  if (INTERNAL_SQL_OR_TRACE_PATTERNS.some((pattern) => lowered.includes(pattern))) {
    return fallback;
  }

  return cleaned;
}
