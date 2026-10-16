# Woka Reel Intelligence — Security, Compliance & Governance

## 1. Authentication & Tenant Authorization
- **JWT Tokens:** HS256-signed JSON Web Tokens with a 60-minute lifetime and explicit `type="access"` validation.
- **Refresh Token Rotation:** Refresh tokens stored hashed in the database; single-use rotation on each refresh.
- **Revocation Store:** Logged-out tokens tracked in a revocation store to prevent replay attacks.
- **Workspace Scoping:** Every private resource (`ReelAnalysisJob`, `ReelMediaAsset`, `ReelReport`, `ReelComparison`) enforces `workspace_id` filtering at the SQL query level. Never trust client-supplied tenant identifiers.

---

## 2. Server-Side Request Forgery (SSRF) Guard
When ingesting external URLs (`/jobs/url`):
1. **Scheme Validation:** Only `http` and `https` schemes permitted.
2. **Domain & Host Validation:**
   - Hostnames matching `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, or cloud metadata services (`169.254.169.254`, `metadata.google.internal`) are blocked.
   - Hostnames are resolved to IP addresses and checked against private/reserved CIDR blocks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `fe80::/10`).
   - Any private target raises `HTTP 422 Unprocessable Content`.

---

## 3. Media Upload Validation & Binary Magic Bytes
When ingesting uploaded video files (`/jobs/upload`):
1. **MIME Whitelisting:** Accepted MIME types strictly restricted to `video/mp4`, `video/quicktime`, `video/webm`, `video/x-m4v`.
2. **Binary Header Inspection:** The first 64 bytes are inspected before persisting:
   - Rejected if header matches executable binaries (`MZ` Windows PE, `\x7fELF` Linux binary, shell scripts `#!/`, PHP, HTML/JS scripts).
   - Validated against container signatures (`ftyp`, `moov`, `mdat`, `wide`, or WebM `\x1a\x45\xdf\xa3`).
3. **Resource Caps:** File sizes capped at 100 MB (`MAX_VIDEO_SIZE_BYTES`).

---

## 4. Meta Instagram Platform Compliance & Data Protection
- **No HTML Scraping:** Woka does not scrape Instagram web pages or attempt to bypass login gates.
- **Token Vault:** Instagram Long-Lived Page Access Tokens are encrypted with AES-256 before persistence using `TOKEN_ENCRYPTION_KEY`.
- **Zero Fabricated Curves:** Where Meta Graph API does not provide second-by-second drop-off retention curves, findings are labeled as creative observations or heuristic retention risks.
- **Data Deletion Compliance:** Implements Meta data deletion callbacks (`/api/v1/instagram/data-deletion`) with trackable confirmation codes.
