# WOKA — Implementation Phases & Roadmap

This document outlines the phased milestone implementation of Woka. Each phase must be verified with automated tests and human review before proceeding to subsequent phases.

---

## Phase 1: Project Foundations & Specifications [COMPLETED]
- [x] Inspect existing directory and initialize structure.
- [x] Create core specifications:
  - `PRD.md`
  - `architecture.md`
  - `database-schema.md`
  - `design-system.md`
  - `implementation-phases.md`
  - `security.md`
  - `testing.md`
  - `DECISIONS.md`
  - `PROGRESS.md`
- **Verification:** All 9 specification files exist, conform to requirements, and establish the architecture.

---

## Phase 2: Backend Core — Setup, Multi-Tenant Auth & Database Layer [IN PROGRESS]
- [ ] Set up Python FastAPI backend in `backend/`.
- [ ] Implement database connectivity with SQLAlchemy 2.0 (supporting SQLite for zero-friction local execution & PostgreSQL for production).
- [ ] Implement complete ORM models (`User`, `Workspace`, `InstagramAccount`, `Automation`, `AutomationLog`, `CreatorAnalytics`, `CreatorProfile`, `BrandCampaign`, `CampaignApplication`, `CampaignDeliverable`, `Invoice`, `Subscription`, `Notification`).
- [ ] Implement password hashing (bcrypt) and JWT token generation (access + refresh).
- [ ] Build Authentication Router (`/api/v1/auth`): Register, Login, Current User (`/me`), Role Switch/Check.
- [ ] Build seed data script with rich creator and brand demo datasets.
- [ ] Write and pass Pytest suite for authentication and multi-tenancy isolation.
- **Verification:** Pytest test suite passes for user registration, login, token refresh, and workspace creation.

---

## Phase 3: Official Meta Instagram Integration Pathway & Webhook Processor
- [ ] Build Instagram OAuth configuration and authorization code generator.
- [ ] Implement OAuth callback exchange (exchanging short-lived token for 60-day Long-Lived Token).
- [ ] Implement AES-256 token encryption and decryption utilities.
- [ ] Implement Meta Webhook verification endpoint (GET with `hub.challenge` and `hub.verify_token`).
- [ ] Implement Meta Webhook event receiver (POST with HMAC-SHA256 signature verification).
- [ ] Build dual-mode Sandbox Engine:
  - Real Meta API mode.
  - Interactive Demo Sandbox with realistic mock accounts, post sync, and simulated comment triggers.
- [ ] Pytest suite for webhook signature validation, idempotency checks, and token encryption.
- **Verification:** Webhook challenge handshake succeeds; simulated and live webhook payloads parse accurately.

---

## Phase 4: Core Domain Services & API Endpoints
- [ ] **Automations Service (`/api/v1/automations`):**
  - CRUD for Comment-to-DM triggers (Keyword rules, custom DM text, cooldown limits).
  - Test run / Simulation endpoint for instant creator preview.
  - Execution logs with status filters (`SUCCESS`, `PENDING`, `RATE_LIMITED`, `FAILED`).
- [ ] **Analytics Service (`/api/v1/analytics`):**
  - Aggregated KPIs (Followers, Reach, Engagement Rate, Impressions).
  - Time series data (7d, 30d, 90d) for Recharts.
  - Top performing posts & audience demographic breakdown.
- [ ] **AI Content Studio (`/api/v1/ai-studio`):**
  - Instagram Caption Generator with customizable tone and CTAs.
  - Viral Reels Hook Generator.
  - Smart Hashtag categorization (High / Mid / Low competition).
- [ ] **Creator Media Kit Service (`/api/v1/media-kit`):**
  - Public profile endpoint (`GET /api/v1/media-kit/{slug}`).
  - Rate card management (Reel, Story, Bundle).
  - Verified creator badge status.
- [ ] **Brand Marketplace & Deliverables (`/api/v1/campaigns`):**
  - Campaign creation and discovery.
  - Application pitching and acceptance.
  - Deliverables tracking with review milestones.
- [ ] **Invoicing & Rate Calculator (`/api/v1/invoices`):**
  - Formula-based rate pricing recommendations.
  - Invoice generation, line items, and payment status update.
- [ ] **Subscriptions & Usage (`/api/v1/subscriptions`):**
  - Quota verification (DMs used, AI generations used).
- [ ] Pytest suite for all business routers.
- **Verification:** All backend endpoints return valid OpenAPI schemas and pass integration test suites.

---

## Phase 5: Frontend Architecture, Theme & Core UI Components
- [ ] Initialize Next.js App Router application with TypeScript and Tailwind CSS in `frontend/`.
- [ ] Implement Woka design tokens (Violet-to-Coral palette, slate typography, card radiuses).
- [ ] Configure accessible UI primitives (Buttons, Inputs, Dialogs, Selects, Badges, Tabs, Toast, Switch).
- [ ] Build shared application shell:
  - Responsive Sidebar with navigation for all 12 modules.
  - Topbar with active workspace switcher, notifications dropdown, and user menu.
  - Persistent Sandbox / Live status badge.
- [ ] Implement API client with automatic JWT token attachment and error interception.
- **Verification:** Next.js compiles with strict TypeScript typing; layout renders cleanly across viewport sizes.

---

## Phase 6: Frontend Feature Modules & Interactive Experiences
- [ ] **Landing Page & Marketing Experience:**
  - Hero section, interactive demo calculator, feature grid, pricing table, FAQs.
- [ ] **Auth & Onboarding:**
  - Login, Sign Up, Role selector (Creator vs Brand vs Agency), Onboarding wizard.
- [ ] **Dashboard Overview:**
  - Quick action shortcuts, active automation performance, recent campaign invites, DM velocity.
- [ ] **Instagram Connection & Automation Builder:**
  - OAuth setup guide, Sandbox toggle, Visual Rule Builder (Keyword tags, DM preview phone mockup), Live test simulator, Execution history table.
- [ ] **Creator Analytics & Insights:**
  - Recharts graphs (Growth curve, Engagement rate, Reach breakdown), Post grid with engagement stats.
- [ ] **AI Content Studio:**
  - Interactive prompt studio, Copy-to-clipboard, Save to drafts, Hashtag pills.
- [ ] **Public Media Kit & Profile:**
  - Public route `/kit/[slug]` with verified metrics, rate cards, and "Work with Me" inquiry form.
- [ ] **Brand Marketplace & Campaign Manager:**
  - Campaign search & filter, Application submission modal, Deliverables submission & review tracker.
- [ ] **Invoices & Rate Calculator:**
  - Interactive pricing estimator slider, Invoice builder, Printable invoice preview.
- [ ] **Billing & Admin Console:**
  - Plan comparison & upgrade modal, Admin overview of platform metrics and user list.
- **Verification:** Every button, modal, form, and tab functions seamlessly with real API backend integration.

---

## Phase 7: System Verification, Testing & Quality Assurance
- [ ] Run full backend Pytest suite.
- [ ] Build and verify frontend production bundle (`npm run build`).
- [ ] Audit user flows against Non-Negotiable Rules (no dead buttons, clear demo banners, secure credentials).
- [ ] Update `PROGRESS.md`, `DECISIONS.md`, and generate user documentation.
