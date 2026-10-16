# Woka — Creator SaaS, Instagram Automation & Brand Collaboration Platform

**Woka** is a production-oriented, multi-tenant creator economy SaaS inspired by the feature categories of Influish. It features an original visual brand identity, modern modular architecture, and compliant official Meta Graph API integration pathways.

---

## 🌟 Key Features

1. **Woka Reel Intelligence:** AI-powered Instagram Reel analysis and optimization platform. Features dual modes (Public URL/Video Upload & Connected Meta Account), computer vision scene cut analysis, speech cadence/WPM tracking, dead-air detection, 4 explainable scores (Creative Quality, Performance, Growth Conversion, Viral Potential), timestamped findings timeline, 3-tier prioritized action plans, and multi-Reel comparison.
2. **Authentication & Multi-Tenancy:** Secure JWT access & refresh tokens, password hashing with bcrypt, role-based access control (`CREATOR`, `BRAND`, `AGENCY`, `ADMIN`), and workspace scoping.
3. **Official Meta Instagram Integration:** Server-side OAuth 2.0 authorization code flow, 60-day Long-Lived Token exchange, AES-256 token encryption at rest, and HMAC-SHA256 signature verification on webhooks.
4. **Interactive Demo Sandbox:** 1-click test mode that generates realistic mock creator accounts, allows simulating comment triggers, and renders live DM previews without waiting for Meta App Review approval.
5. **Instagram Comment-to-DM Automation:** Keyword matching rules (Exact, Contains Any, Any Comment), personalized variables (`{{username}}`), public comment replies, and anti-spam cooldown intervals.
6. **Interactive Trigger Simulator:** In-app sandbox phone mockup simulator to test comment responses and verify execution logs in real-time.
7. **Creator Analytics & Reach:** 30-day time-series growth curves with Recharts, audience age/gender demographic breakdowns, and top-performing Reels sorted by engagement rate.
8. **AI Content Studio:** Generative captions with custom tone controls, 5 viral Reels hook frameworks (Curiosity Gap, Contrarian, Blueprint), and smart reach-tiered hashtag buckets.
9. **Public Creator Media Kit:** Public vanity link (`/kit/[slug]`) featuring verified Meta follower stats, audience reach, deliverable rate cards, and an interactive "Work with Me" brand inquiry form.
10. **Brand Collaboration Marketplace:** Discover active campaigns, filter by niche and budget, submit creative pitches and deliverable milestones (`REEL`, `STORY`, `BUNDLE`).
11. **Invoicing & Smart Rate Calculator:** Defensible CPM-based pricing calculator and itemized invoice generator with 1-click payment status tracking (`DRAFT`, `SENT`, `PAID`).
12. **Subscription & Quota Management:** Real-time usage meters for comment automations and AI generations across `FREE`, `PRO`, and `AGENCY` tiers.
13. **Admin Operations & Telemetry:** Platform overview of registered users, active automations, webhook throughput, and infrastructure latency.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js** (v18+ or v20+)
- **Python** (v3.10+)

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # On Windows (or source venv/bin/activate on Unix)

# Install dependencies
pip install -r requirements.txt

# Seed the database with demo creators, campaigns, and automations
python -m app.seed

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Documentation (OpenAPI/Swagger): `http://localhost:8000/api/v1/docs`
- Health check: `http://localhost:8000/api/health`

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
- Web Application: `http://localhost:3000`
- Reel Intelligence: `http://localhost:3000/dashboard/reel-intelligence`

---

## 🔑 Pre-Configured Demo Accounts

You can log in with 1-click from the `/login` page using these credentials:

| Role | Email | Password | Details |
|---|---|---|---|
| **Creator** | `creator@woka.io` | `Creator123!` | Alex Rivera (48.5k followers, active automations & media kit) |
| **Brand** | `brand@luminaudio.com` | `Brand123!` | Lumin Audio Tech (active sponsor campaigns & proposals) |
| **Admin** | `admin@woka.io` | `Admin123!` | Woka Operations (platform telemetry & user moderation) |

Public Demo Media Kit Link: `http://localhost:3000/kit/alexrivera`

---

## 🧪 Running Automated Tests

### Backend Test Suite (Pytest)
```bash
cd backend
.\venv\Scripts\python -m pytest -v
```
All 50 test cases cover:
- Woka Reel Intelligence metric formulas, edge cases (0 views/missing reach), audio speech WPM, AI diagnosis scoring ranges, job submission, comparison engine, and tenant isolation
- User registration, login, JWT claims, and token revocation
- Tenant isolation and permission checks
- Comment-to-DM trigger matching and simulator engine
- Meta Webhook handshake (`hub.challenge`) and HMAC signature validation
- AES-256 token encryption and decryption roundtrip
- Rate pricing calculator formulas and invoice calculations
- Meta reviewer privilege enforcement and data deletion compliance

### Frontend Test Suite & Production Build
```bash
cd frontend
npm test
npm run build
```
All 11 unit/integration tests cover formatting, regex shortcode validators, and score tier thresholds. Next.js App Router static build verification passes cleanly.

---

## 📂 Project Architecture Documentation

All specifications, architectural designs, and decision records are maintained in the repository root:
- `REEL_INTELLIGENCE.md`: Complete architecture and specification for Woka Reel Intelligence
- `PRD.md`: Complete Product Requirements Document across all modules
- `architecture.md`: Modular monolith system diagram, Meta OAuth flow, and multi-tenancy
- `database-schema.md`: Complete data dictionary including Reel Intelligence models
- `design-system.md`: Design tokens, Violet-to-Coral palette, typography, and card specifications
- `security.md`: Meta compliance, AES-256 encryption, HMAC signatures, and RBAC
- `testing.md`: Quality assurance and automated testing strategy
- `DECISIONS.md`: Architectural Decision Records (ADRs 001–006)
- `PROGRESS.md`: Phase status and milestone tracking
- `docker-compose.yml`: Production container deployment configuration
