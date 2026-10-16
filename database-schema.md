# WOKA — Database Schema & Data Dictionary

This document details the relational database design for Woka. The schema is implemented using SQLAlchemy 2.0 with migration scripts managed by Alembic, designed to run seamlessly on both PostgreSQL and SQLite.

```mermaid
erDiagram
    USERS ||--o{ WORKSPACE_MEMBERS : has
    WORKSPACES ||--o{ WORKSPACE_MEMBERS : contains
    WORKSPACES ||--o{ INSTAGRAM_ACCOUNTS : links
    WORKSPACES ||--o{ AUTOMATIONS : owns
    AUTOMATIONS ||--o{ AUTOMATION_LOGS : generates
    WORKSPACES ||--o{ CREATOR_ANALYTICS : snapshots
    WORKSPACES ||--o1 CREATOR_PROFILES : publishes
    WORKSPACES ||--o{ BRAND_CAMPAIGNS : creates
    WORKSPACES ||--o{ CAMPAIGN_APPLICATIONS : applies
    BRAND_CAMPAIGNS ||--o{ CAMPAIGN_APPLICATIONS : receives
    CAMPAIGN_APPLICATIONS ||--o{ CAMPAIGN_DELIVERABLES : tracks
    WORKSPACES ||--o{ INVOICES : bills
    WORKSPACES ||--o1 SUBSCRIPTIONS : holds
    USERS ||--o{ NOTIFICATIONS : receives
```

---

## 1. Table Definitions

### 1.1 `users`
Represents platform user credentials, role, and profile state.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) / UUID | PRIMARY KEY | Unique user identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Primary email address |
| `hashed_password` | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| `full_name` | VARCHAR(120) | NOT NULL | User's legal or public name |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'CREATOR' | Role: `CREATOR`, `BRAND`, `AGENCY`, `ADMIN` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active flag |
| `is_verified` | BOOLEAN | NOT NULL, DEFAULT FALSE | Email verification status |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Registration timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last modification |

---

### 1.2 `workspaces` & `workspace_members`
Enforces strict multi-tenancy and agency team delegation.
**`workspaces`**
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Unique workspace UUID |
| `name` | VARCHAR(120) | NOT NULL | Workspace or creator handle name |
| `owner_id` | VARCHAR(36) | FOREIGN KEY -> `users.id` | Primary workspace owner |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Creation timestamp |

**`workspace_members`**
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Membership record ID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id` | Target workspace |
| `user_id` | VARCHAR(36) | FOREIGN KEY -> `users.id` | Invited user |
| `role_in_workspace` | VARCHAR(20) | NOT NULL, DEFAULT 'MEMBER' | `OWNER`, `ADMIN`, `MEMBER` |

---

### 1.3 `instagram_accounts`
Stores official Meta Instagram Business/Creator account links.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Record UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, NOT NULL | Parent workspace |
| `ig_user_id` | VARCHAR(64) | NOT NULL, INDEX | Official Instagram Business Account ID |
| `username` | VARCHAR(100) | NOT NULL, INDEX | Instagram handle (e.g. `@tech_alex`) |
| `name` | VARCHAR(120) | NULLABLE | Display name on Instagram |
| `profile_pic_url` | TEXT | NULLABLE | CDN profile avatar URL |
| `encrypted_access_token` | TEXT | NOT NULL | AES-256 encrypted Graph API access token |
| `token_expires_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Expiry timestamp of 60-day token |
| `is_connected` | BOOLEAN | NOT NULL, DEFAULT TRUE | Live connection status |
| `is_sandbox` | BOOLEAN | NOT NULL, DEFAULT FALSE | Flag indicating if this is a simulated demo account |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Connection timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update timestamp |

---

### 1.4 `automations`
Comment-to-DM triggers and rule definitions.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Automation UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, NOT NULL | Parent workspace |
| `ig_account_id` | VARCHAR(36) | FOREIGN KEY -> `instagram_accounts.id` | Linked Instagram account |
| `name` | VARCHAR(150) | NOT NULL | Internal label (e.g. "Free E-Book Giveaway") |
| `trigger_type` | VARCHAR(30) | NOT NULL, DEFAULT 'COMMENT' | `COMMENT`, `STORY_REPLY`, `MENTION` |
| `target_post_type` | VARCHAR(30) | NOT NULL, DEFAULT 'SPECIFIC_POST' | `ALL_POSTS`, `SPECIFIC_POST`, `NEXT_POST` |
| `target_post_id` | VARCHAR(100) | NULLABLE | Instagram Media ID or Shortcode |
| `target_post_preview_url` | TEXT | NULLABLE | Thumbnail image URL |
| `match_type` | VARCHAR(30) | NOT NULL, DEFAULT 'CONTAINS_ANY' | `EXACT_MATCH`, `CONTAINS_ANY`, `CONTAINS_ALL`, `ANY_COMMENT` |
| `trigger_keywords` | JSON / TEXT | NOT NULL | Array of triggers, e.g. `["link", "guide", "free"]` |
| `dm_message_template` | TEXT | NOT NULL | Outbound DM text with variables |
| `reply_comment_template` | TEXT | NULLABLE | Optional public reply to the comment |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable toggle |
| `cooldown_minutes` | INTEGER | NOT NULL, DEFAULT 60 | Anti-spam cooldown per recipient |
| `total_triggered_count`| INTEGER | NOT NULL, DEFAULT 0 | Cumulative successful executions |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Timestamp |

---

### 1.5 `automation_logs`
Execution history and audit trail for all triggered automations.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Log entry UUID |
| `automation_id` | VARCHAR(36) | FOREIGN KEY -> `automations.id`, NOT NULL | Triggered automation |
| `recipient_ig_id` | VARCHAR(64) | NOT NULL | Instagram Scoped ID of recipient |
| `recipient_username` | VARCHAR(100) | NOT NULL | Recipient username |
| `trigger_comment_id` | VARCHAR(64) | NULLABLE | Comment ID that initiated trigger |
| `trigger_comment_text`| TEXT | NULLABLE | Exact text left by user |
| `dm_text_sent` | TEXT | NOT NULL | Processed DM text sent |
| `status` | VARCHAR(30) | NOT NULL | `SUCCESS`, `PENDING`, `RATE_LIMITED`, `FAILED`, `SIMULATED` |
| `error_message` | TEXT | NULLABLE | Detailed error payload if failed |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW(), INDEX | Trigger timestamp |

---

### 1.6 `creator_analytics`
Historical metrics snapshots for chart generation.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Metric record UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, NOT NULL | Parent workspace |
| `snapshot_date` | DATE | NOT NULL, INDEX | Recorded calendar date |
| `followers_count` | INTEGER | NOT NULL, DEFAULT 0 | Total followers on this date |
| `following_count` | INTEGER | NOT NULL, DEFAULT 0 | Following count |
| `media_count` | INTEGER | NOT NULL, DEFAULT 0 | Total active posts |
| `reach_30d` | INTEGER | NOT NULL, DEFAULT 0 | Total 30-day reach |
| `impressions_30d` | INTEGER | NOT NULL, DEFAULT 0 | Total 30-day impressions |
| `avg_engagement_rate`| FLOAT | NOT NULL, DEFAULT 0.0 | Calculated ER% |
| `demographics_json` | JSON / TEXT | NULLABLE | Age, gender, country distribution |
| `top_posts_json` | JSON / TEXT | NULLABLE | Top 5 performing posts metadata |

---

### 1.7 `creator_profiles`
Public media kit and marketplace presentation card.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Profile UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, UNIQUE | Parent workspace |
| `slug` | VARCHAR(80) | UNIQUE, NOT NULL, INDEX | URL handle: `/kit/[slug]` |
| `display_name` | VARCHAR(120) | NOT NULL | Creator name |
| `bio` | TEXT | NULLABLE | About the creator & channel focus |
| `avatar_url` | TEXT | NULLABLE | Creator avatar |
| `niches` | JSON / TEXT | NOT NULL | Tags, e.g. `["Tech", "Productivity", "SaaS"]` |
| `location` | VARCHAR(100) | NULLABLE | City, Country |
| `rate_reel` | DECIMAL(10,2)| DEFAULT 0.00 | Dedicated Reel standard price ($) |
| `rate_story` | DECIMAL(10,2)| DEFAULT 0.00 | Story sequence price ($) |
| `rate_bundle` | DECIMAL(10,2)| DEFAULT 0.00 | Reel + Story + Link bundle ($) |
| `is_verified` | BOOLEAN | NOT NULL, DEFAULT FALSE | Verified stats badge |
| `is_public` | BOOLEAN | NOT NULL, DEFAULT TRUE | Public visibility toggle |

---

### 1.8 `brand_campaigns`
Marketplace campaigns posted by brands.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Campaign UUID |
| `brand_workspace_id`| VARCHAR(36) | FOREIGN KEY -> `workspaces.id` | Posting brand |
| `title` | VARCHAR(200) | NOT NULL | Campaign title |
| `description` | TEXT | NOT NULL | Brief, deliverables, guidelines |
| `niche` | VARCHAR(60) | NOT NULL, INDEX | Category / industry |
| `budget_min` | DECIMAL(10,2)| NOT NULL | Minimum compensation |
| `budget_max` | DECIMAL(10,2)| NOT NULL | Maximum compensation |
| `required_deliverables`| JSON / TEXT| NOT NULL | e.g. `["1x Reel", "2x Stories"]` |
| `submission_deadline`| DATE | NOT NULL | Deadline for creator proposals |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'OPEN' | `OPEN`, `IN_PROGRESS`, `COMPLETED`, `CLOSED` |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Timestamp |

---

### 1.9 `campaign_applications` & `campaign_deliverables`
Tracks creator applications and content review milestones.
**`campaign_applications`**
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Application UUID |
| `campaign_id` | VARCHAR(36) | FOREIGN KEY -> `brand_campaigns.id` | Applied campaign |
| `creator_workspace_id`| VARCHAR(36)| FOREIGN KEY -> `workspaces.id` | Applying creator |
| `pitch_text` | TEXT | NOT NULL | Why creator is a fit |
| `proposed_rate` | DECIMAL(10,2)| NOT NULL | Quoted compensation |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'APPLIED'| `APPLIED`, `ACCEPTED`, `REJECTED`, `COMPLETED` |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Application timestamp |

**`campaign_deliverables`**
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Deliverable UUID |
| `application_id` | VARCHAR(36) | FOREIGN KEY -> `campaign_applications.id` | Parent application |
| `deliverable_type` | VARCHAR(50) | NOT NULL | `REEL`, `STORY`, `POST`, `CAROUSEL` |
| `live_url` | TEXT | NULLABLE | Live Instagram link |
| `preview_asset_url` | TEXT | NULLABLE | Draft video or image upload |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'PENDING' | `PENDING`, `SUBMITTED`, `IN_REVIEW`, `APPROVED`, `REVISION_REQUESTED` |
| `feedback_notes` | TEXT | NULLABLE | Brand revision notes |
| `submitted_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Submission timestamp |

---

### 1.10 `invoices`
Creator invoicing, deliverable billing, and payment tracking.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Invoice UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id` | Issuing creator workspace |
| `invoice_number` | VARCHAR(50) | NOT NULL, INDEX | Human readable, e.g. `INV-2026-001` |
| `client_name` | VARCHAR(150) | NOT NULL | Brand or Agency name |
| `client_email` | VARCHAR(255) | NOT NULL | Billing email |
| `total_amount` | DECIMAL(10,2)| NOT NULL | Total payable |
| `currency` | VARCHAR(10) | NOT NULL, DEFAULT 'USD' | Currency code |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'DRAFT' | `DRAFT`, `SENT`, `PAID`, `OVERDUE`, `CANCELLED` |
| `due_date` | DATE | NOT NULL | Payment deadline |
| `line_items_json` | JSON / TEXT | NOT NULL | Array of `{description, quantity, unit_price, total}` |
| `notes` | TEXT | NULLABLE | Wire transfer or payment notes |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Creation timestamp |

---

### 1.11 `subscriptions`
Tier entitlements and real-time usage quotas.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Subscription UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, UNIQUE | Parent workspace |
| `plan_tier` | VARCHAR(30) | NOT NULL, DEFAULT 'FREE' | `FREE`, `PRO`, `AGENCY` |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `TRIALING`, `PAST_DUE`, `CANCELLED` |
| `dm_limit_monthly` | INTEGER | NOT NULL, DEFAULT 50 | Monthly comment-to-DM cap |
| `dm_used_monthly` | INTEGER | NOT NULL, DEFAULT 0 | Count consumed in billing period |
| `ai_limit_monthly` | INTEGER | NOT NULL, DEFAULT 10 | AI copy generation quota |
| `ai_used_monthly` | INTEGER | NOT NULL, DEFAULT 0 | Count consumed in billing period |
| `current_period_end`| TIMESTAMP WITH TIME ZONE | NULLABLE | Next reset date |

---

### 1.12 `notifications`
Real-time alerts and activity stream.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Notification UUID |
| `user_id` | VARCHAR(36) | FOREIGN KEY -> `users.id`, INDEX | Target user |
| `title` | VARCHAR(150) | NOT NULL | Alert title |
| `message` | TEXT | NOT NULL | Notification body |
| `category` | VARCHAR(40) | NOT NULL | `AUTOMATION`, `CAMPAIGN`, `INVOICE`, `SYSTEM` |
| `link` | VARCHAR(255) | NULLABLE | Actionable target URL |
| `is_read` | BOOLEAN | NOT NULL, DEFAULT FALSE | Read indicator |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Timestamp |

---

### 1.13 `reel_media_assets`
Ingested and processed media assets (video uploads, public reels, thumbnail frames) associated with a workspace.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Asset UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, INDEX | Parent workspace |
| `source_type` | VARCHAR(30) | NOT NULL | `PUBLIC_URL`, `VIDEO_UPLOAD`, `CONNECTED_ACCOUNT` |
| `original_url` | TEXT | NULLABLE | Original external URL (if applicable) |
| `storage_path` | VARCHAR(500) | NULLABLE | Local or S3 path to video file |
| `thumbnail_path` | VARCHAR(500) | NULLABLE | Extracted or downloaded thumbnail image path |
| `file_size_bytes` | BIGINT | NULLABLE | Video file size |
| `mime_type` | VARCHAR(100) | NULLABLE | e.g. `video/mp4`, `video/quicktime` |
| `duration_seconds` | FLOAT | NULLABLE | Detected video duration |
| `width` | INTEGER | NULLABLE | Pixel width |
| `height` | INTEGER | NULLABLE | Pixel height |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Ingestion timestamp |

---

### 1.14 `reel_analysis_jobs`
Asynchronous processing jobs tracking the multi-stage analysis pipeline.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Job UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, INDEX | Parent workspace |
| `asset_id` | VARCHAR(36) | FOREIGN KEY -> `reel_media_assets.id` | Target media asset |
| `mode` | VARCHAR(30) | NOT NULL | `PUBLIC_URL`, `VIDEO_UPLOAD`, `CONNECTED_ACCOUNT` |
| `instagram_media_id` | VARCHAR(100) | NULLABLE | Connected Meta Media ID |
| `status` | VARCHAR(30) | NOT NULL | `QUEUED`, `INGESTING`, `PROCESSING_VIDEO`, `ANALYZING_METRICS`, `GENERATING_AI_REPORT`, `COMPLETED`, `FAILED` |
| `progress_percent` | INTEGER | NOT NULL, DEFAULT 0 | 0 to 100 completion percentage |
| `status_message` | VARCHAR(255) | NULLABLE | Active stage descriptor |
| `error_details` | TEXT | NULLABLE | Error message and traceback on failure |
| `retry_count` | INTEGER | NOT NULL, DEFAULT 0 | Job retry attempts |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Queued timestamp |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Finished timestamp |

---

### 1.15 `reel_metric_snapshots`
Time-series metric captures for growth velocity and historical baseline comparisons.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Snapshot UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, INDEX | Parent workspace |
| `instagram_media_id` | VARCHAR(100) | NULLABLE, INDEX | Meta media object ID |
| `views_count` | INTEGER | NOT NULL, DEFAULT 0 | View / play count |
| `reach_count` | INTEGER | NULLABLE | Unique viewer reach (authorized mode only) |
| `likes_count` | INTEGER | NOT NULL, DEFAULT 0 | Like count |
| `comments_count` | INTEGER | NOT NULL, DEFAULT 0 | Comment count |
| `shares_count` | INTEGER | NULLABLE | Share count |
| `saves_count` | INTEGER | NULLABLE | Save/bookmark count |
| `total_watch_time_seconds`| FLOAT | NULLABLE | Aggregated watch time |
| `average_watch_time_seconds`| FLOAT | NULLABLE | Mean retention watch time |
| `follows_attributed` | INTEGER | NULLABLE | Follows gained directly from Reel |
| `profile_visits_attributed` | INTEGER | NULLABLE | Profile visits from Reel |
| `captured_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Snapshot timestamp |

---

### 1.16 `reel_reports`
Comprehensive, production-grade intelligence reports combining video findings, scorecards, and action plans.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Report UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, INDEX | Parent workspace |
| `job_id` | VARCHAR(36) | FOREIGN KEY -> `reel_analysis_jobs.id`, UNIQUE | Originating analysis job |
| `asset_id` | VARCHAR(36) | FOREIGN KEY -> `reel_media_assets.id` | Target media asset |
| `title` | VARCHAR(255) | NOT NULL | Video title or caption headline |
| `caption` | TEXT | NULLABLE | Extracted or submitted caption |
| `analysis_mode` | VARCHAR(30) | NOT NULL | `PUBLIC_URL`, `VIDEO_UPLOAD`, `CONNECTED_ACCOUNT` |
| `scores_json` | JSON / TEXT | NOT NULL | 4 distinct scores (Creative, Performance, Growth, Viral) |
| `calculated_metrics_json` | JSON / TEXT | NOT NULL | Documented rates with numerator/denominator |
| `video_intelligence_json` | JSON / TEXT | NOT NULL | Scene cuts, lighting, WPM, safe-zone hazards |
| `timeline_findings_json` | JSON / TEXT | NOT NULL | Timestamped observations and proposed edits |
| `prioritized_action_plan_json` | JSON / TEXT | NOT NULL | 3-tier prioritized what/why/how action items |
| `creative_alternatives_json` | JSON / TEXT | NOT NULL | 4 Hook frameworks, thumbnails, CTAs, revised scripts |
| `provenance_json` | JSON / TEXT | NOT NULL | Pipeline version, models, data limitations |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Generation timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update timestamp |

---

### 1.17 `reel_comparisons`
Multi-Reel comparative analysis reports (2 to 5 Reels).
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Comparison UUID |
| `workspace_id` | VARCHAR(36) | FOREIGN KEY -> `workspaces.id`, INDEX | Parent workspace |
| `report_ids_json` | JSON / TEXT | NOT NULL | Array of compared Report UUIDs |
| `comparison_matrix_json` | JSON / TEXT | NOT NULL | Side-by-side metric comparison |
| `comparative_takeaways_json`| JSON / TEXT | NOT NULL | Actionable differential takeaways |
| `winner_id` | VARCHAR(36) | NULLABLE | Top-performing report ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Creation timestamp |
