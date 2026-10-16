# Woka Reel Intelligence — System Architecture

## 1. High-Level Architecture Overview

Woka Reel Intelligence is built as a high-performance modular monolith with an asynchronous video and data processing pipeline.

```mermaid
flowchart TD
    subgraph Client ["Client Presentation Layer (Next.js 14 App Router)"]
        UI["Web App (Tailwind CSS, TypeScript)"]
        AuthViews["Login / Register / OAuth Callback"]
        Dashboard["Analysis Dashboard & Comparison Studio"]
    end

    subgraph API ["API & Security Gateway (FastAPI)"]
        Router["FastAPI Application Router (/api/v1)"]
        AuthMiddleware["JWT Bearer Authentication & RBAC"]
        SSRFGuard["SSRF & URL Whitelist Validator"]
        UploadValidator["Binary Magic Byte Inspector (100MB limit)"]
    end

    subgraph Workers ["Media & Intelligence Pipeline"]
        JobOrchestrator["Background Job Orchestrator"]
        VideoEngine["OpenCV & Scene Segmentation Engine"]
        AudioEngine["Acoustic Cadence & Dead-Air Detector"]
        OCREngine["OCR Text & Subtitle Safe-Zone Engine"]
        MetricEngine["Mathematical Rate & Baseline Engine"]
        DiagnosisEngine["Explainable Scoring & AI Generator"]
    end

    subgraph Storage ["Persistence & Data Store"]
        PostgreSQL[("PostgreSQL 16 / SQLite (Relational Store)")]
        RedisStore[("Redis 7 (Job Queue & Cache)")]
        Vault[("AES-256 Token Store")]
        MediaStore["Local Disk / S3 Media Storage"]
    end

    subgraph External ["External Services"]
        MetaAPI["Official Meta Graph API"]
        AIProvider["Configurable AI Provider / Deterministic Fallback"]
    end

    UI --> Router
    Router --> AuthMiddleware --> SSRFGuard --> UploadValidator
    UploadValidator --> JobOrchestrator
    JobOrchestrator --> VideoEngine
    JobOrchestrator --> AudioEngine
    JobOrchestrator --> OCREngine
    JobOrchestrator --> MetricEngine
    JobOrchestrator --> DiagnosisEngine

    VideoEngine --> MediaStore
    MetricEngine --> MetaAPI
    DiagnosisEngine --> AIProvider

    JobOrchestrator --> PostgreSQL
    JobOrchestrator --> RedisStore
    Router --> Vault
```

---

## 2. Asynchronous Job State Machine

To ensure long-running media processing never blocks FastAPI HTTP request threads, jobs transition through strict states:

```mermaid
stateDiagram-v2
    [*] --> QUEUED: Job Created (URL or Upload)
    QUEUED --> INGESTING: Container Inspection (15%)
    INGESTING --> PROCESSING_VIDEO: OpenCV Frame Sampling & Audio Analysis (45%)
    PROCESSING_VIDEO --> ANALYZING_METRICS: Ingest Meta Insights & Baseline Deltas (70%)
    ANALYZING_METRICS --> GENERATING_AI_REPORT: Compute 8 Scores & Action Plan (90%)
    GENERATING_AI_REPORT --> COMPLETED: Persist Report & Notify Client (100%)
    
    INGESTING --> FAILED: Invalid Container / Timeout
    PROCESSING_VIDEO --> FAILED: Media Decoding Error
    ANALYZING_METRICS --> FAILED: API Rate Limit / Network Loss
    GENERATING_AI_REPORT --> FAILED: Schema Validation Error
    FAILED --> QUEUED: Retry Job (/jobs/{id}/retry)
    COMPLETED --> [*]
```

---

## 3. Data Flow & Security Boundary

1. **Ingestion Boundary:**
   - Public URLs are checked against SSRF IP filters before any outbound socket connection is made.
   - Uploaded files are inspected for container magic bytes (`ftyp`, `moov`, `mdat`, EBML) to prevent executable execution.
2. **Execution Boundary:**
   - Jobs are isolated to the caller's user and workspace ID.
   - Cross-tenant queries are blocked at the database layer.
3. **Storage Boundary:**
   - Sensitive Meta Page Access Tokens are encrypted with AES-256 using `TOKEN_ENCRYPTION_KEY` at rest.
