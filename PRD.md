# WOKA — Product Requirements Document (PRD)

## 1. Executive Summary & Product Vision
**Product Name:** Woka  
**Category:** Creator Growth, Instagram Automation, AI Creator Tools, Influencer Analytics & Brand Collaboration SaaS  
**Tagline:** *"Woka helps creators grow smarter, automate Instagram engagement, understand their performance, and discover brand opportunities—all from one workspace."*

Woka is a multi-tenant web-first software-as-a-service (SaaS) platform built specifically for the creator economy. Influencer creators lose dozens of hours every week manually responding to post comments, sending direct message links, guessing brand rates, negotiating sponsorships over fragmented DMs, and compiling manual PDF media kits. 

Woka unifies:
1. **Engagement Automation:** Compliant Comment-to-DM Instagram automation via official Meta Graph APIs.
2. **Deep Analytics:** Actionable insights into follower growth, engagement rates, and content velocity.
3. **AI Content Studio:** Generative copy, hooks, and hashtag recommendations tailored for Instagram formats.
4. **Creator Media Kit & Rate Card:** Dynamic, verified, shareable public media kits with live statistics.
5. **Brand Marketplace:** Direct campaign matching, milestone-driven deliverable submission, and transparent payouts.
6. **Financial Operations:** Smart deliverable pricing calculators, invoice generation, and status tracking.

---

## 2. Target Personas

### Persona A: Solo Creator / Influencer (Alex, 45k followers)
- **Goal:** Monetize engagement from viral Reels, convert comments into newsletter subscribers/digital sales, and pitch brands professionally.
- **Pain Points:** Spends 3 hours/day sending "Check DM for link!", gets underpaid by brands due to lack of standard pricing metrics, struggles to maintain a dynamic media kit.

### Persona B: Direct-to-Consumer Brand / Marketer (Elena, Brand Lead)
- **Goal:** Launch influencer marketing campaigns with verified creators, track deliverables, avoid fraud, and manage campaign budgets efficiently.
- **Pain Points:** Cluttered spreadsheets, creators ghosting deliverables, lack of standardized post-performance verification.

### Persona C: Creator Management Agency (Marcus, Agency Director)
- **Goal:** Manage 10+ creators, monitor client automation limits, standardize media kits, and generate client invoices in bulk.
- **Pain Points:** Multi-account fragmentation, permissions management, lack of consolidated reporting.

### Persona D: Platform Administrator (Woka Operations)
- **Goal:** Monitor platform health, manage abuse or spam triggers, inspect Meta API rate limits, audit webhook processing, and resolve disputed campaigns.

---

## 3. Product Modules & Functional Specifications

### Module 1: Authentication & Multi-Tenant Onboarding
- **Specs:**
  - Email/password authentication with bcrypt hashing and JWT tokens (access + refresh tokens).
  - Role-based access control (RBAC): `CREATOR`, `BRAND`, `AGENCY`, `ADMIN`.
  - Workspace tenant isolation: Creators have private workspaces; Agencies have multi-creator rosters.
  - Interactive onboarding wizard: Profile setup, niche selection, follower bracket, primary goals.

### Module 2: Meta Instagram Account Connection
- **Specs:**
  - Official Meta Graph API & Instagram Messaging API OAuth 2.0 flow.
  - Permissions requested: `instagram_basic`, `instagram_manage_comments`, `instagram_manage_messages`, `pages_show_list`, `pages_read_engagement`.
  - Secure state token validation for CSRF mitigation.
  - AES-256 encrypted storage of long-lived access tokens.
  - Token refresh management (Meta tokens expire in 60 days).
  - Webhook registration for `mentions`, `comments`, and `messaging`.
  - **Dual Mode (Production & Demo Sandbox):** Clear UI toggle allowing users to test with real Meta OAuth or instantly explore with sandbox mock data and simulated webhook events without requiring an active Meta App Review.

### Module 3: Instagram Comment-to-DM Automation Engine
- **Specs:**
  - Trigger configuration:
    - Post targeting (All Posts, Specific Post/Reel ID).
    - Keyword matching (Exact match, contains keyword, any comment).
  - Response actions:
    - Automated comment reply (optional public response variation).
    - Automated Instagram DM dispatch with personalized variables (`{{username}}`, `{{link}}`, `{{code}}`).
    - Anti-spam guard: Configurable response delay (randomized 5–30s) and per-user frequency limits.
  - Execution History & Audit Log:
    - Status (`SUCCESS`, `PENDING`, `RATE_LIMITED`, `FAILED`), timestamp, user handle, trigger keyword, and delivery verification.

### Module 4: Creator Analytics & Performance Insights
- **Specs:**
  - Metric tracking: Total Followers, Follower Growth Velocity, Reach, Impressions, Engagement Rate (ER%).
  - Post breakdown: Top performing Reels/Posts sorted by comments, saves, and shares.
  - Historical charting: Interactive 7-day, 30-day, and 90-day time-series graphs via Recharts.
  - Audience Demographics: Age distribution, top geographic countries, active hours.
  - Visual indicator flags identifying real Meta Graph sync vs. simulated sandbox dataset.

### Module 5: AI Content Studio
- **Specs:**
  - Post Caption Generator: Tone selection (Engaging, Witty, Professional, Storytelling, Urgent), target call-to-action (CTA), emoji controls.
  - Viral Hook Generator: Reels opening hooks based on high-retention creator frameworks.
  - Hashtag Optimizer: Niche-specific hashtags categorized by reach tiers (Low, Medium, High competition).
  - Content Calendar Planner: Draft storage and scheduling status (`DRAFT`, `PLANNED`, `PUBLISHED`).

### Module 6: Creator Profile & Dynamic Public Media Kit
- **Specs:**
  - Public shareable profile URL (`/kit/[username]`).
  - Bio, primary niches, social links, audience demographics summary.
  - Verified Statistics Badge (showing authentic Meta API sync or Verified Creator status).
  - Standard Deliverable Rate Cards (e.g., Reel + Story bundle, Dedicated Reel, Link-in-Bio placement).
  - Direct "Work With Me" inquiry modal triggering campaign collaboration leads.

### Module 7: Brand Collaboration Marketplace
- **Specs:**
  - Brand Campaign Publisher: Budget range, target niche, deliverable requirements, submission deadline.
  - Creator Discovery & Marketplace Feed: Filter campaigns by niche (Fashion, Tech, Fitness, Lifestyle, etc.), minimum compensation, and deadline.
  - Application Flow: Creator pitch submission, rate offer, and estimated turnaround.

### Module 8: Campaign Deliverables & Milestone Workflow
- **Specs:**
  - Milestone stages: `APPLIED` -> `OFFER_ACCEPTED` -> `CONTENT_SUBMITTED` -> `IN_REVIEW` -> `APPROVED` -> `COMPLETED`.
  - Deliverable link submission: Live Instagram Post/Reel URL submission with preview.
  - In-app feedback & revision requests between brand and creator.

### Module 9: Invoices & Smart Rate Calculator
- **Specs:**
  - Dynamic Creator Rate Calculator: Formula based on follower count, average reach, engagement rate, and deliverable format.
  - Invoice Generator: Client name, line items, taxes, due date, payment instructions.
  - Invoice status tracking (`DRAFT`, `SENT`, `PAID`, `OVERDUE`).
  - Print/PDF export view.

### Module 10: Subscriptions & Usage Management
- **Specs:**
  - Tier structure:
    - **Free Tier:** 1 Instagram account, 50 automated DMs/mo, basic analytics, 10 AI generations.
    - **Pro Creator ($29/mo):** 3 Instagram accounts, 2,000 automated DMs/mo, advanced analytics, unlimited AI, public media kit.
    - **Agency / Brand ($99/mo):** Unlimited accounts, 20,000 automated DMs/mo, campaign marketplace creation, team members.
  - Real-time usage meters with visual quota warnings.

### Module 11: Real-time Notifications & Activity Center
- **Specs:**
  - Notification triggers: New automation trigger fired, campaign application received, proposal accepted, deliverable approved, subscription alerts.
  - Filterable notification list with read/unread status.

### Module 12: Admin & Operations Console
- **Specs:**
  - Platform KPIs: Total users, total automations active, total DMs dispatched, active campaigns.
  - User and account management with suspension/verification toggles.
  - Webhook monitoring: Ingestion health, failed webhook replay, latency stats.

---

## 4. Non-Functional Requirements
- **Performance:** Sub-200ms API response time for typical CRUD queries. Under 1.5s initial page load on 4G connections.
- **Security:** OAuth tokens encrypted with AES-256 at rest; zero client-side secret exposure; CSRF tokens on OAuth callbacks; HMAC-SHA256 signature verification on webhooks.
- **Compliance:** Strict adherence to Meta Platform Terms and Instagram Platform Policy (no scraping, no private API exploitation, user opt-in messaging).
- **Reliability:** Idempotent webhook processing to prevent duplicate DM dispatch.
- **Accessibility:** WCAG 2.1 AA compliant contrast ratios, accessible form controls, keyboard navigability.
