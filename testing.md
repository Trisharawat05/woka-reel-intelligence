# WOKA — Testing Strategy & Quality Assurance Plan

## 1. Testing Philosophy
Woka employs automated testing at all architectural boundaries to ensure high reliability, zero data contamination between tenants, and flawless webhook processing.

### Testing Principles:
- **No False Claims:** Never claim a feature works without passing automated tests and manual verification.
- **Isolated State:** Every test run operates against an isolated database transaction or in-memory SQLite store.
- **Mock External Networks:** Official Meta API endpoints and external LLM services are mocked during CI/CD to prevent flaky tests and external API dependency.

---

## 2. Test Suite Structure

```
backend/tests/
├── conftest.py            # Fixtures: DB session, TestClient, Auth tokens, Mock Meta responses
├── test_auth.py           # Register, login, duplicate email, password hash, invalid token
├── test_workspace.py      # Multi-tenant scoping and cross-tenant access prevention
├── test_instagram.py      # OAuth URL generation, token encryption/decryption, sandbox toggle
├── test_webhooks.py       # Meta challenge verification, HMAC signature validation, idempotency
├── test_automations.py    # Rule matching (contains, exact), cooldown limits, simulation engine
├── test_analytics.py      # Metric calculations, snapshot ingestion, demo data fallbacks
├── test_campaigns.py      # Campaign creation, creator pitches, deliverable approval cycle
└── test_invoices.py       # Rate calculator formulas, invoice lifecycle (draft -> sent -> paid)
```

---

## 3. Core Test Scenarios

### 3.1 Authentication & Multi-Tenancy Tests
1. **User Registration:** Creates user, generates default workspace, issues JWT access token.
2. **Duplicate Email Rejection:** Ensures 400 Bad Request on duplicate email registration.
3. **Password Security:** Verifies password is never returned in response schemas.
4. **Tenant Isolation:** Creator A cannot view, update, or delete Creator B's automations or invoices (404/403 expected).

### 3.2 Meta Integration & Webhook Integrity Tests
1. **Webhook Challenge Verification:** Correct `hub.verify_token` responds with `hub.challenge`; incorrect token returns 403 Forbidden.
2. **HMAC Signature Check:** Valid `X-Hub-Signature-256` succeeds; modified or missing header returns 401 Unauthorized.
3. **Comment Trigger Matching:**
   - Inbound comment containing `"link"` matches automation keyword `["link", "guide"]`.
   - Inbound comment without trigger word does not dispatch DM.
4. **Frequency Cooldown:** Second comment from same user within cooldown window is suppressed.
5. **Token Encryption:** Persisted token in database does not match raw token; decrypted value exactly matches raw token.

### 3.3 Business Logic & Calculations Tests
1. **Rate Calculator Formula:** Validates standard influencer pricing equation based on follower tier and engagement rate multipliers.
2. **Deliverables Workflow State Machine:** Enforces valid transitions (`APPLIED` -> `ACCEPTED` -> `SUBMITTED` -> `APPROVED`). Invalid transitions (e.g. `APPLIED` directly to `APPROVED`) are rejected.
3. **Quota Enforcement:** Free tier user attempting to dispatch >50 DMs receives quota exceeded error.

---

## 4. Test Execution Instructions

### Backend (Pytest)
```bash
# Navigate to backend
cd backend

# Run all test suites
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

### Frontend (Build & Type Verification)
```bash
# Navigate to frontend
cd frontend

# Verify TypeScript types and build
npm run build
```
