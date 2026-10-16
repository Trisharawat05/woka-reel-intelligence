# Woka Reel Intelligence — API Specification

Base URL: `/api/v1`  
Authentication: HTTP Bearer JWT in `Authorization` header.

---

## 1. Authentication Endpoints (`/auth`)

| Method | Endpoint | Request Body | Description |
|---|---|---|---|
| `POST` | `/auth/register` | `{"email", "password", "full_name", "role"}` | Registers a new user and generates default workspace |
| `POST` | `/auth/login` | `{"username", "password"}` (form-urlencoded) | Authenticates user and returns JWT access & refresh tokens |
| `POST` | `/auth/refresh` | `{"refresh_token"}` | Rotates refresh token and issues new access token |
| `POST` | `/auth/logout` | `{"refresh_token"}` | Revokes refresh token and terminates session |
| `GET` | `/auth/me` | None | Returns active user profile and workspace metadata |

---

## 2. Reel Intelligence Endpoints (`/reel-intelligence`)

### 2.1 Submit Public Reel URL
`POST /api/v1/reel-intelligence/jobs/url`  
**Request:**
```json
{
  "url": "https://www.instagram.com/reel/C8xyzABC123/",
  "declared_views": 15000,
  "declared_likes": 1200,
  "declared_comments": 85,
  "declared_shares": 140,
  "declared_saves": 320
}
```
**Response (202 Accepted):**
```json
{
  "id": "job_uuid_123",
  "workspace_id": "ws_uuid_456",
  "analysis_mode": "PUBLIC_URL",
  "input_type": "url",
  "status": "QUEUED",
  "progress_percent": 5,
  "stage_message": "Analysis job queued",
  "source_url": "https://www.instagram.com/reel/C8xyzABC123/",
  "created_at": "2026-10-16T10:00:00Z"
}
```

### 2.2 Upload Video File
`POST /api/v1/reel-intelligence/jobs/upload`  
**Request:** `multipart/form-data` with `file: UploadFile` (.mp4, .mov, .webm $\le$ 100MB).  
**Response (202 Accepted):** Analysis job schema with `analysis_mode="VIDEO_UPLOAD"`.

### 2.3 Submit Connected Account Reel
`POST /api/v1/reel-intelligence/jobs/connected`  
**Request:**
```json
{
  "media_id": "ig_reel_101",
  "title": "3 Hook Mistakes That Kill Your Retention",
  "caption": "Why you need to cut breaths...",
  "media_url": "https://...",
  "thumbnail_url": "https://..."
}
```
**Response (202 Accepted):** Analysis job schema with `analysis_mode="CONNECTED_ACCOUNT"`.

### 2.4 Poll Job Status
`GET /api/v1/reel-intelligence/jobs/{job_id}`  
Returns real-time progress (0–100%), stage message, and `report_id` once completed.

### 2.5 Retrieve Final Report
`GET /api/v1/reel-intelligence/reports/{report_id}`  
Returns full report object with:
- 8 Core Score breakdowns with component contributions.
- Calculated metrics with documented numerators and denominators.
- Video intelligence features (cuts, WPM, safe zones).
- Timestamped findings timeline.
- Prioritized 3-tier action plan.
- Creative alternatives (hooks, thumbnails, captions, revised scripts).
- Data source provenance and disclaimers.

### 2.6 List Report History
`GET /api/v1/reel-intelligence/reports?search={query}&mode={mode}&limit=50&offset=0`  
Returns list of past reports in the workspace.

### 2.7 Multi-Reel Comparison
`POST /api/v1/reel-intelligence/compare`  
**Request:**
```json
{
  "report_ids": ["report_id_1", "report_id_2"]
}
```
**Response (200 OK):**
```json
{
  "id": "comp_uuid_789",
  "reports": [...],
  "winner_id": "report_id_1",
  "comparison_matrix": { "total_compared": 2, "winner_title": "..." },
  "comparative_takeaways": [
    "'Reel A' outperformed other Reels primarily due to higher Hook Retention Velocity...",
    "Videos adhering to Instagram 9:16 safe zones experienced superior watch completion..."
  ]
}
```

### 2.8 Retry Failed Analysis
`POST /api/v1/reel-intelligence/jobs/{job_id}/retry`  
Resets failed job to `QUEUED` and re-initiates the pipeline.
