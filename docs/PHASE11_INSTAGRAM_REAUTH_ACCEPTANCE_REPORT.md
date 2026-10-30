# Woka Reel Intelligence — Phase 11: Instagram Reauthorization & Live Media Verification Report

**Execution Date**: 2026-10-30  
**Auditor**: Antigravity Full-Stack & Meta Platform Integration Specialist  
**Repository**: `woka-reel-intelligence` (`C:\Users\Trisha\OneDrive\Desktop\Woka - Reel Analyzer`)  
**Base Commit**: `aaa33fe`  
**API Target**: Meta Instagram Graph API `v25.0` / `v21.0`  
**Document Classification**: Comprehensive Technical Audit & Acceptance Report  

---

## 1. Executive Summary & Audit Matrix

Following Phase 10's discovery of Meta API error code 190 (`OAuthException: The session has been invalidated because the user changed their password or Facebook has changed the session for security reasons`), Phase 11 audits the end-to-end reauthorization lifecycle, cryptographic state protection, token storage encryption, single-record database idempotency, and live media verification under strict zero-fabrication constraints.

In strict compliance with our core operating directives:
1. **Zero Fabrication**: No simulated responses or synthetic metrics are represented as live API data. Live probe results are recorded as actual raw status returns.
2. **Zero Secret Exposure**: No access tokens, client secrets, webhook verify tokens, or encryption keys are logged, printed, or committed.
3. **Honest Status Accounting**: Automated tests, mocked verification, and live external probes are strictly distinguished.

### Verification Status Table

| Audit Dimension | Target Subsystem | Status | Key Evidence / Rationale |
| :--- | :--- | :---: | :--- |
| **OAuth Flow & Scopes** | `instagram_service.py` | **PASS** | Official Instagram Login for Business endpoint configured with `instagram_business_basic` and `instagram_business_manage_insights`. |
| **CSRF & Nonce Protection** | HMAC-SHA256 State & Nonce Tracker | **PASS** | HMAC-signed state with timestamp validation (900s TTL) and single-use nonce tracking to prevent replay attacks. |
| **Token Exchange & Long-Lived Token** | Meta Token Exchange Endpoints | **PASS** | Short-lived token exchange (`/oauth/access_token`) and conversion to 60-day token (`/access_token?grant_type=ig_exchange_token`) verified in unit tests. |
| **At-Rest Token Encryption** | Fernet AES-256-GCM | **PASS** | Tokens encrypted before database write; plaintext never persisted in logs or database tables. |
| **Reauthorization Idempotency** | Database Account Update | **PASS** | Verified in `test_reauthorization_updates_account_in_place_without_duplicates`: Existing record updated in place; 0 duplicate rows created. |
| **Disconnected Account Handling** | Deauthorization & Deletion Webhooks | **PASS** | Webhooks parse `signed_request`, verify HMAC signature, and zeroize stored tokens. |
| **Connect Instagram UI** | `frontend/.../dashboard/instagram` | **PASS** | Added prominent reauthorization warning banner and "Reauthorize Instagram Account" CTA directly to dashboard action toolbar. |
| **Automated Backend Regression** | Pytest Test Suite | **PASS** | **104 passed, 1 skipped** in 31.77s across 105 tests. |
| **Automated Frontend Regression** | Jest & TypeScript Typecheck | **PASS** | **14 passed** (184ms) in Jest; **0 errors** in `npx tsc --noEmit`. |
| **Live Instagram Media Request** | `GET /api/v1/instagram/media` | **BLOCKED** | Token from Phase 10 returned HTTP 400 (Error 190, fbtrace_id: `ANMiBH9SMCBlWPAkPqKjlje`). Blocked pending user reauthorization with live credentials. |
| **Live Insights Retrieval** | `GET /api/v1/instagram/sync-insights` | **BLOCKED** | Blocked on valid active access token; zero synthetic multiplier fallback enforced. |

---

## 2. OAuth Architecture & Security Lifecycle

### 2.1 State & Nonce Cryptographic Generation
Woka secures all OAuth authorization attempts against CSRF and replay attacks:
```python
state_payload = {
    "workspace_id": workspace_id,
    "timestamp": int(datetime.now(timezone.utc).timestamp()),
    "nonce": str(uuid.uuid4())
}
```
1. **HMAC-SHA256 Signature**: The payload is serialized to canonical JSON, signed with `settings.SECRET_KEY`, and base64-encoded as `<b64_payload>.<hmac_signature>`.
2. **TTL Expiration**: Verified upon callback; timestamps older than 900 seconds or more than 60 seconds in the future are rejected.
3. **Workspace Binding**: The embedded `workspace_id` must match the authenticated user's workspace, preventing cross-tenant authorization hijacking.
4. **Single-Use Nonce Tracking**: Used nonces are persisted in `used_oauth_nonces`, preventing authorization replay attacks.

### 2.2 Token Exchange & Expiry Metadata
Upon receiving an authorization code from Meta:
1. **Step 1 — Short-Lived Token Exchange**:
   - URL: `POST https://api.instagram.com/oauth/access_token`
   - Payload: `client_id`, `client_secret`, `grant_type=authorization_code`, `redirect_uri`, `code`
   - Returns: short-lived access token (~1 hour), `user_id`, and granted permissions.
2. **Step 2 — 60-Day Long-Lived Token Exchange**:
   - URL: `GET https://graph.instagram.com/access_token`
   - Params: `grant_type=ig_exchange_token`, `client_secret`, `access_token`
   - Returns: long-lived access token (~60 days / 5,184,000 seconds).
3. **Step 3 — Timezone-Aware Expiry Persistence**:
   - Computed as `datetime.now(timezone.utc) + timedelta(seconds=expires_in)`.
   - Stored in `InstagramAccount.token_expires_at` with UTC timezone awareness.

### 2.3 At-Rest Token Encryption
- Plaintext access tokens are encrypted using Fernet (AES-256-GCM symmetric encryption) via `app.security.encrypt_token()`.
- The database stores only the ciphertext in `InstagramAccount.encrypted_access_token`.
- Plaintext tokens are decrypted strictly in memory when dispatching authorized requests to Meta Graph API and immediately discarded.

### 2.4 Idempotent Reauthorization & Zero Duplicate Records
When a user initiates reauthorization for an existing workspace:
- `connect_or_update_account_from_oauth()` queries `InstagramAccount` by `workspace_id`.
- If an existing record is present (whether active, expired, or disconnected), it updates the record fields in place:
  - `account.encrypted_access_token = new_encrypted_token`
  - `account.token_expires_at = new_expires_at`
  - `account.granted_permissions = new_permissions`
  - `account.is_connected = True`
  - `account.is_sandbox = False`
  - `account.updated_at = datetime.now(timezone.utc)`
- `db.add()` is skipped; only `db.commit()` is executed.
- Verified in automated test `test_reauthorization_updates_account_in_place_without_duplicates`: total account row count remained exactly 1 before and after reauthorization.

### 2.5 Disconnected Account & Deauthorization Handling
- **User Disconnect**: `POST /api/v1/instagram/disconnect` sets `is_connected = False`, zeroizes `encrypted_access_token = ""`, and nullifies `token_expires_at`.
- **Meta Deauthorization Callback**: `POST /api/v1/instagram/deauthorize` parses Meta's `signed_request`, validates the HMAC signature using `META_APP_SECRET`, extracts the `user_id`, and marks the account disconnected.
- **Meta Data Deletion Callback**: `POST /api/v1/instagram/data-deletion` wipes stored tokens and generates a unique tracking code (`woka_del_<uuid>`) and deletion confirmation URL.
- **Runtime Error 190 Mapping**: When any API edge returns Meta error 190 (`OAuthException`), the service catches the error, sets `account.is_connected = False`, commits to the database, and raises `HTTP 401 Unauthorized` with a reauthorization required prompt.

---

## 3. Meta Platform & API Version Alignment

| Configuration Parameter | Woka Configured Setting | Meta Platform Standard | Compliance |
| :--- | :--- | :--- | :---: |
| **OAuth Flow** | `instagram_business` | Instagram Login for Business | **MATCH** |
| **OAuth Dialog Host** | `https://www.instagram.com/oauth/authorize` | Official Meta Instagram OAuth URL | **MATCH** |
| **Dialog Parameters** | `enable_fb_login=0&force_authentication=1` | Meta Recommended for Direct IG Auth | **MATCH** |
| **Code Exchange Host** | `https://api.instagram.com/oauth/access_token` | Official Instagram OAuth Edge | **MATCH** |
| **Graph API Host** | `https://graph.instagram.com` | Official Instagram Graph API Host | **MATCH** |
| **API Version** | `v21.0` through `v25.0` | Active Supported Meta API Versions | **MATCH** |
| **Requested Permissions** | `instagram_business_basic`, `instagram_business_manage_insights` | Minimal Necessary Scopes for Reel Insights | **MATCH** |

---

## 4. Connect Instagram UI Enhancements

The frontend at `frontend/src/app/dashboard/instagram/page.tsx` was enhanced to handle token invalidation and streamline reauthorization:

1. **Prominent Reauthorization Banner**:
   - Detects `isTokenExpired || account?.is_token_expired`.
   - Renders a high-visibility amber alert banner:
     *"Meta Instagram Access Token Invalidated or Expired: The access token session has ended or was invalidated by Meta (e.g. security session reset, password change, or 60-day expiry). Reauthorize to restore live media retrieval and insights sync."*
   - Includes a direct "Reauthorize Instagram" button that initiates `handleStartMetaOAuth()`.

2. **Action Toolbar Integration**:
   - When the token is expired or invalidated, the Action Toolbar dynamically highlights a primary **Reauthorize Account Now** button in amber.
   - When the token is healthy, an option for **Reauthorize / Switch Account** remains accessible alongside "Sync Insights Now" and "Refresh 60-Day Token".

3. **Status Diagnostic Card**:
   - The "Token Expiration" card dynamically flags "Requires reauthorization" whenever the token is expired or revoked.

---

## 5. Live Media & Insights Status: BLOCKED

### 5.1 Live Probe Evidence
A live HTTP probe was executed against `https://graph.instagram.com/v25.0/17841458643277126/media`:

```json
{
  "error": {
    "message": "Error validating access token: The session has been invalidated because the user changed their password or Facebook has changed the session for security reasons.",
    "type": "OAuthException",
    "code": 190,
    "error_subcode": 0,
    "fbtrace_id": "ANMiBH9SMCBlWPAkPqKjlje"
  }
}
```

- **HTTP Status**: `400 Bad Request`
- **Error Code**: `190`
- **fbtrace_id**: `ANMiBH9SMCBlWPAkPqKjlje`
- **Status Classification**: `BLOCKED`

### 5.2 Zero-Fabrication Rule Enforcement
In accordance with rule 8 (*Do not fabricate API responses, analytics, engagement metrics, retention curves, test results, or completed work*) and rule 9 (*Never silently substitute mock data when a real service fails*):
- Media items are not fabricated.
- Views are not multiplied by `likes * 10`.
- The live endpoint `GET /api/v1/instagram/media` and insight synchronizer `POST /api/v1/instagram/sync-insights` will return 401 until a valid active token is supplied via user reauthorization.

---

## 6. Verification Test Suite Matrix

```
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\Trisha\OneDrive\Desktop\Woka - Reel Analyzer\backend
plugins: anyio-4.15.1, asyncio-1.4.0
collected 105 items

tests\test_auth.py .....                                                 [  4%]
tests\test_auth_hardened.py ...                                          [  7%]
tests\test_automations.py ...                                            [ 10%]
tests\test_backup_restore.py .                                           [ 11%]
tests\test_campaigns_invoices.py ....                                    [ 15%]
tests\test_meta_oauth_and_insights.py ................................s. [ 47%]
.....                                                                    [ 52%]
tests\test_meta_reviewer_privileges.py .....                             [ 57%]
tests\test_reel_intelligence.py .................                        [ 73%]
tests\test_staging_validation.py ..............                          [ 86%]
tests\test_state_machines.py ....                                        [ 90%]
tests\test_tenant_isolation.py ...                                       [ 93%]
tests\test_webhooks.py ....                                              [ 97%]
tests\test_webhooks_hardened.py ...                                      [100%]

================= 104 passed, 1 skipped, 7 warnings in 31.77s =================
```

| Suite | Component | Tests Run | Result | Duration |
| :--- | :--- | :---: | :---: | :---: |
| **Backend Pytest** | Full Backend Test Suite | 105 items (104 pass, 1 skip) | **PASS** | 31.77s |
| **Backend Pytest** | `test_reauthorization_updates_account_in_place_without_duplicates` | 1 item | **PASS** | 0.53s |
| **Frontend Jest** | Component & Utility Tests | 14 items | **PASS** | 184ms |
| **Frontend TSC** | TypeScript Strict Compilation (`npx tsc --noEmit`) | Entire Frontend Codebase | **PASS (0 errors)** | ~50s |

---

## 7. Actionable Steps to Complete Live Reauthorization

To unblock the live media and insights retrieval:

### Option 1: Complete Live OAuth in Browser (Standard Flow)
1. **Configure Meta App Credentials**:
   Ensure `META_APP_ID` and `META_APP_SECRET` are set in `backend/.env` with your real Meta Developer App credentials (not `mock_*`).
2. **Launch Application**:
   - Backend: `uvicorn app.main:app --reload --port 8000`
   - Frontend: `npm run dev` (running on `http://localhost:3000`)
3. **Trigger Reauthorization**:
   - Navigate to `http://localhost:3000/dashboard/instagram`.
   - Click **Reauthorize Instagram Account**.
   - Authenticate with the Instagram Professional/Creator account.
4. **Verify Live Data**:
   - Upon redirect, the dashboard will display `@your_handle` as connected with an active 60-day token.
   - Click **Sync Insights Now** to fetch live Reel metrics.

### Option 2: Generate Fresh Token via Meta Graph API Explorer
If running in a headless or restricted environment:
1. Open the [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Select your Meta App and generate a User Token with scopes `instagram_business_basic` and `instagram_business_manage_insights`.
3. Exchange for a 60-day long-lived token:
   ```bash
   curl -X GET "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=YOUR_APP_SECRET&access_token=YOUR_SHORT_LIVED_TOKEN"
   ```
4. Update the stored token in your environment or database, and trigger `GET /api/v1/instagram/media`.
