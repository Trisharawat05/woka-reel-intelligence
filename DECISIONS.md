# WOKA — Architectural & Technical Decision Records (ADRs)

This document tracks all significant architectural, technological, and design decisions made throughout the lifecycle of the Woka project.

---

### ADR-001: Modular Monolith vs Microservices
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The platform requires multiple distinct functional domains (Instagram Automation, Creator Analytics, AI Studio, Brand Marketplace, Invoicing, Admin).
- **Decision:** Build as a clean **Modular Monolith** with a single FastAPI backend application and Next.js frontend, separated by domain service boundaries.
- **Rationale:** Prevents distributed system overhead, network latency, distributed transactions, and deployment complexity. Independent domain modules can be extracted later if traffic demands it.

---

### ADR-002: Dual-Compatibility Database Engine (SQLite & PostgreSQL)
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Developers and reviewers need to run and test the complete application instantly without external Docker or PostgreSQL server dependencies, while production requires robust relational PostgreSQL capabilities.
- **Decision:** Standardize on SQLAlchemy 2.0 with dynamic engine configuration: SQLite for zero-config local development/testing and PostgreSQL for production deployments via `DATABASE_URL`.
- **Rationale:** Ensures 100% testability out of the box with `sqlite:///./woka.db` while maintaining full compatibility with cloud PostgreSQL.

---

### ADR-003: Dual-Mode Official Meta Instagram Integration & Sandbox
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Official Meta Graph API permissions (`instagram_manage_messages`, `instagram_manage_comments`) require Meta App Review, Business Verification, and live webhooks, which creates friction for local testing and evaluation.
- **Decision:** Implement the complete official Meta OAuth 2.0 and Webhook signature verification pathway, paired with an interactive **Demo Sandbox Simulator**.
- **Rationale:** Allows complete, real-time testing of the Comment-to-DM engine, webhook handlers, and analytics without needing an immediate approved Meta App ID, while providing an instant plug-and-play pathway when official Meta credentials are provided.

---

### ADR-004: AES-256 Symmetric Encryption for OAuth Access Tokens
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Meta 60-day Long-Lived Page Access Tokens grant control over messaging and comments.
- **Decision:** Encrypt all access tokens at rest using AES-256 (Fernet) before writing to the database. Tokens are decrypted in-memory only when dispatching an outbound API call.
- **Rationale:** Protects creator credentials even if a database snapshot is compromised.

---

### ADR-005: Resilient AI Content Studio Architecture
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The AI Content Studio generates captions, viral hooks, and hashtags. External LLM APIs can be unavailable, rate-limited, or lack API keys in local development.
- **Decision:** Design a multi-tiered generator service: checks for configured LLM API keys; if absent or failing, seamlessly falls back to a deterministic, high-quality creator template and NLP heuristics engine.
- **Rationale:** Zero downtime, zero crashed requests, and instant creative output for users in any deployment environment.

---

### ADR-006: Visual Brand Direction (Violet-to-Coral Accent System)
- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Creator tools often rely on generic dark-mode or overwhelming neon gradients.
- **Decision:** Adopt an airy, light-slate background (`#F8FAFC`) with deep high-contrast slate typography (`#0F172A`) and a signature restrained Violet (`#7C3AED`) to Coral (`#F43F5E`) accent spectrum.
- **Rationale:** Maximum legibility for analytics tables and deliverable reviews, with vibrant visual cues for primary action triggers.
