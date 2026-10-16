# Woka Reel Intelligence — Staging Deployment & Operations Guide

This guide details the end-to-end procedure for deploying **Woka Reel Intelligence** to a staging environment, configuring live Meta Instagram Graph API credentials, verifying health and readiness probes, and performing post-deployment smoke testing.

---

## 1. Architecture & Staging Topology

```mermaid
flowchart TD
    User["Creator / Reviewer Browser"] -->|HTTPS| Cloudflare["Edge / CDN / Cloudflare"]
    Cloudflare -->|staging.woka.io| Vercel["Next.js 14 App Router (Frontend)"]
    Cloudflare -->|api-staging.woka.io| Backend["FastAPI Container (PaaS / ECS / Cloud Run)"]
    
    Backend -->|SQLAlchemy 2.x Pool| Postgres[("Managed PostgreSQL 16 (RDS / Neon)")]
    Backend -->|Background Tasks / Cache| Redis[("Managed Redis 7 (Upstash / ElastiCache)")]
    Backend -->|OAuth 2.0 & Insights (v21.0/v22.0)| MetaAPI["Meta Graph API (graph.instagram.com)"]
    Backend -->|File Storage (Videos/Thumbs)| S3["Media Storage (S3 / Local Volume)"]

    subgraph Health Probes
        Orchestrator["Container Orchestrator"] -->|GET /healthz| Backend
        Orchestrator -->|GET /readyz (DB Ping)| Backend
    end
```

### Staging Component Responsibilities

| Component | Technology | Target Staging Host | Port / Protocol |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js 14, TypeScript, Tailwind | Vercel / Node Container | 443 (HTTPS) |
| **Backend API** | FastAPI, Python 3.10+, Uvicorn | AWS ECS / GCP Cloud Run / Render | 8000 &rarr; 443 |
| **Database** | PostgreSQL 16 | AWS RDS / Neon / Supabase | 5432 (SSL Mode Required) |
| **Cache / Queue** | Redis 7 | AWS ElastiCache / Upstash | 6379 (TLS) |
| **Storage** | Object Storage / Volume | S3-compatible / EBS | HTTPS |

---

## 2. Pre-Deployment Environment Checklist

Before triggering a deployment, ensure all required environment secrets are provisioned in your secrets manager (e.g., AWS Secrets Manager, GitHub Secrets, or Infisical).

### Required Environment Variables

```ini
# Core Configuration
ENVIRONMENT=staging
DEBUG=false
PROJECT_NAME="Woka Reel Intelligence (Staging)"
VERSION=1.0.0
API_V1_STR=/api/v1

# Security & Cryptography
# Generate: openssl rand -hex 32
SECRET_KEY=stg_sec_0192837465abcdeffedcba5647382910fedcba9876543210
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=gAAAAABn...your_32_byte_base64_fernet_key...=
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# URLs & Domains
FRONTEND_URL=https://staging.woka.io
CORS_ORIGINS=["https://staging.woka.io","https://staging-admin.woka.io"]

# Database & Cache (Strictly use TLS in staging/production)
DATABASE_URL=postgresql://woka_user:secure_pass@db.staging.internal:5432/woka_staging?sslmode=require
REDIS_URL=rediss://default:secure_redis_pass@redis.staging.internal:6379/0

# Meta Instagram Graph API (v21.0 / v22.0)
META_APP_ID=123456789012345
META_APP_SECRET=your_meta_app_secret_here
META_VERIFY_TOKEN=woka_staging_meta_webhook_verify_token_2026
# Dual redirect URI support: Backend direct or Frontend exchange
META_REDIRECT_URI=https://staging.woka.io/dashboard/instagram/callback
META_API_VERSION=v21.0

# Rate Limiting & Storage
RATE_LIMIT_PER_MINUTE=120
STORAGE_LOCAL_ROOT=/data/woka_storage
MAX_UPLOAD_SIZE_BYTES=104857600
```

> [!CAUTION]
> The application startup sequence validates `SECRET_KEY` and `TOKEN_ENCRYPTION_KEY`. If `ENVIRONMENT=staging` or `production` and placeholder values (`"mock_"`, `"change-this"`, `"your_token..."`) are detected, the backend will fail fast with a fatal startup error to prevent data compromise.

---

## 3. Database Migration Procedure

Alembic manages all schema revisions. Migrations must be executed prior to switching traffic to the new backend release.

### Running Migrations

```bash
# From CI/CD pipeline or deployment runner
cd backend
python -m alembic upgrade head
```

### Validating Current Revision
```bash
python -m alembic current
# Expected head revision: c8194ad51e7f (adds_reel_intelligence_models)
```

### Rollback Command (If required)
```bash
# Downgrades to previous schema version
python -m alembic downgrade -1
```

---

## 4. Container Probes & Orchestration

The backend application provides explicit liveness and readiness endpoints for Kubernetes, AWS ECS, GCP Cloud Run, and Docker health checks.

### Liveness Probe (`GET /healthz`)
- **Purpose**: Verifies that the Uvicorn process is responsive and serving requests.
- **Path**: `/healthz`
- **Expected Status**: `200 OK`
- **Response**: `{"status": "alive"}`
- **Configuration Recommendation**:
  - Initial delay: 5s
  - Period: 10s
  - Timeout: 2s
  - Failure threshold: 3

### Readiness Probe (`GET /readyz`)
- **Purpose**: Executes `SELECT 1` against PostgreSQL to confirm operational database connectivity before receiving traffic.
- **Path**: `/readyz`
- **Expected Status**: `200 OK` (or `503 Service Unavailable` if database is down)
- **Response**: `{"status": "ready", "database": "connected", "version": "1.0.0", "environment": "staging"}`
- **Configuration Recommendation**:
  - Initial delay: 5s
  - Period: 10s
  - Timeout: 3s
  - Failure threshold: 2

---

## 5. Meta Developer Portal Staging Configuration

To enable staging authorization and insights synchronization:

### 1. Canonical OAuth Callback Architecture
Woka Reel Intelligence implements a direct, secure backend OAuth redirect architecture:

```
[User Browser] ---> (Clicks Connect) ---> [FastAPI: GET /api/v1/instagram/oauth-url]
                                                           |
[User Browser] <--- (Redirects to Meta Dialog) <-----------+ (Contains redirect_uri=https://woka-api-staging.onrender.com/api/v1/instagram/callback)
      |
[Meta Auth Dialog] (User grants instagram_business_basic & instagram_business_manage_insights)
      |
[Meta API] -------> (Redirects with code & HMAC state) ---> [FastAPI: GET /api/v1/instagram/callback]
                                                                      |
                                                               (Validates HMAC & single-use nonce)
                                                               (Exchanges code -> short -> 60-day token)
                                                               (Encrypts token with AES-256 Fernet)
                                                               (Persists InstagramAccount in DB)
                                                                      |
[User Browser] <--- (HTTP 302 Redirect: /dashboard/instagram?connected=true) -+
```

### 2. Register Staging Redirect URIs
In the [Meta for Developers Portal](https://developers.facebook.com/) under **Instagram Login for Business > Settings > Valid OAuth Redirect URIs**:
- **Primary Canonical Backend Callback**: `https://woka-api-staging.onrender.com/api/v1/instagram/callback`
- **Frontend Callback Fallback**: `https://woka-staging.vercel.app/dashboard/instagram/callback`
- **Local Dev Callback**: `http://localhost:8000/api/v1/instagram/callback`

> [!IMPORTANT]
> The environment variable `META_REDIRECT_URI` configured in Render MUST match the registered callback URI character-for-character. The token exchange POST request to `https://api.instagram.com/oauth/access_token` verifies exact matching against the initial authorization request.

### 3. Configure Compliance Callbacks
Under **App Settings > Basic**:
- **Data Deletion Callback URL**: `https://woka-api-staging.onrender.com/api/v1/instagram/data-deletion`
- **Deauthorize Callback URL**: `https://woka-api-staging.onrender.com/api/v1/instagram/deauthorize`

### 4. Configure Webhooks
Under **Instagram > Webhooks**:
- **Callback URL**: `https://woka-api-staging.onrender.com/api/v1/instagram/webhook`
- **Verify Token**: Matching `META_VERIFY_TOKEN` (e.g. generated in Render Blueprint)
- **Subscribed Fields**: `comments`, `messages`

### 5. Assign Tester Accounts
While in **Development Mode** (prior to Meta App Review):
- Add staging test Instagram accounts under **App Roles > Roles > Instagram Testers**.
- Have each tester log in to Instagram (web or app), navigate to **Settings > Apps and Websites > Tester Invites**, and click **Accept**.
- Test accounts MUST be Instagram Professional (Creator or Business) accounts.

---

## 6. Step-by-Step Staging Smoke Test Protocol

Run these verification steps immediately after staging deployment:

### Test 1: Container Health Probes
```bash
# Liveness Probe
curl -i https://woka-api-staging.onrender.com/healthz
# Expected: HTTP 200 {"status": "alive"}

# Readiness Probe (with live DB Ping)
curl -i https://woka-api-staging.onrender.com/readyz
# Expected: HTTP 200 {"status": "ready", "database": "connected", "version": "1.0.0"}
```

### Test 2: Authentication & Workspace Creation
```bash
curl -i -X POST https://woka-api-staging.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "smoke-tester@woka.io",
    "password": "StagingPassword2026!",
    "full_name": "Staging Tester",
    "role": "CREATOR"
  }'
# Expected: HTTP 201 Created with JWT tokens and workspace ID
```

### Test 3: Public Reel Analysis Pipeline
```bash
# Submit job
curl -i -X POST https://woka-api-staging.onrender.com/api/v1/reel-intelligence/jobs/url \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/C8xyzABC123/",
    "declared_views": 18500
  }'
# Expected: HTTP 202 Accepted with job status "QUEUED"
```

### Test 4: Video Upload Magic Bytes Validation
```bash
# Upload disguised binary (must reject)
curl -i -X POST https://woka-api-staging.onrender.com/api/v1/reel-intelligence/jobs/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@fake_video.mp4;type=video/mp4"
# Expected: HTTP 422 Unprocessable Content (Magic bytes validation failed)
```

### Test 5: Meta Instagram Login OAuth & Insights Sync
1. Open `https://woka-staging.vercel.app/dashboard/instagram` in a browser.
2. Click **Connect via Meta OAuth**.
3. Verify redirect to Meta consent dialog showing `instagram_business_basic` and `instagram_business_manage_insights`.
4. Authorize with the Meta Tester Account.
5. Confirm redirect to `https://woka-staging.vercel.app/dashboard/instagram?connected=true&username=...`.
6. Click **Sync Insights Now** and verify metric snapshots populate.
7. Click **Refresh 60-Day Token** and verify expiration updates.
8. Click **Disconnect Account** and verify access tokens are zeroized from the database.

---

## 7. Rollback & Migration Safety Strategy

### 7.1 Traffic & Service Rollback
If critical defects or telemetry regressions occur:
1. **Frontend (Vercel)**:
   - Navigate to Vercel Dashboard > Project > Deployments.
   - Click **...** next to previous stable deployment > **Promote to Production** (takes effect in <5s).
2. **Backend (Render)**:
   - Navigate to Render Dashboard > `woka-api-staging` > Deploys.
   - Click **Rollback to this deploy** on the previous stable commit.

### 7.2 Database Migration Safety & Rollback Warning
> [!CAUTION]
> **NEVER blindly run `alembic downgrade -1` in staging or production.**
> Inspect the target revision before executing downgrades:
> - Revision `c8194ad51e7f` &rarr; drops `granted_permissions` column from `instagram_accounts`.
> - Revision `bd03f60aa48b` &rarr; **DROPS ALL 5 REEL INTELLIGENCE TABLES** (`reel_comparisons`, `reel_metric_snapshots`, `reel_analysis_jobs`, `reel_reports`, `reel_media_assets`), permanently destroying all historical reports!

#### Safe Migration Rollback Protocol:
1. **Pre-Rollback Database Backup**:
   Always take a database snapshot or run `pg_dump` before performing schema downgrades:
   ```bash
   pg_dump "$DATABASE_URL" > pre_rollback_backup_$(date +%s).sql
   ```
2. **Targeted Revision Downgrade**:
   Specify the exact revision identifier instead of relative offsets:
   ```bash
   python -m alembic downgrade bd03f60aa48b
   ```
3. **Additive-First Philosophy**:
   For schema changes, prefer backwards-compatible additive migrations over column/table drops to permit zero-downtime rollbacks without database destruction.
