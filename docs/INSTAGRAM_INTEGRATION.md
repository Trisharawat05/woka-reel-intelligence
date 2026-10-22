# Woka Reel Intelligence — Instagram Graph API Integration Guide

## 1. Architectural Overview & Source of Truth

The primary source of truth for Instagram media retrieval in **Woka Reel Intelligence** is the verified Meta Graph API user media edge:

```http
GET https://graph.instagram.com/{api_version}/{user_id}/media?fields=id,caption,media_type,media_url,permalink,timestamp&limit=10&access_token={access_token}
```

### Verified Request Specifications
- **HTTP Method**: `GET`
- **Host**: `https://graph.instagram.com`
- **Supported API Versions**: `v21.0` through `v25.0` (configurable via `META_API_VERSION`)
- **Target Node**: `/{user_id}/media` (where `user_id` is an Instagram Scoped User ID / IGSID, or `/me/media` for the authenticated token holder)
- **Authentication**: `access_token` query parameter or `Authorization: Bearer {token}` HTTP header
- **Required Permission**: `instagram_business_basic`

---

## 2. Field Mapping & Schema Definition

The `/media` edge returns a paginated collection of published Instagram media assets. Only fields actually returned by Meta are mapped into the application domain:

| Field Name | Type | Description | Woka Usage |
| :--- | :--- | :--- | :--- |
| `id` | `string` | Unique Instagram Media ID | Stored as `source_media_id` in `ReelAnalysisJob` and `ReelMetricSnapshot` |
| `caption` | `string` | Caption and post text | Used for transcript heuristics, keyword extraction, and CTA analysis |
| `media_type` | `string` | `VIDEO`, `IMAGE`, or `CAROUSEL_ALBUM` | Filter for Reel candidate selection (`media_type == "VIDEO"`) |
| `media_url` | `string` | Direct CDN media stream URL | Ingestion source for computer-vision and pacing analysis |
| `permalink` | `string` | Public web URL (`https://www.instagram.com/reel/...`) | Verification link in dashboard and deep-linking |
| `timestamp` | `string` | ISO-8601 publication timestamp | Published date timeline and decay rate calculation |
| `thumbnail_url` | `string` (optional) | Video cover frame image URL | Reel Intelligence report cover thumbnail |

> [!IMPORTANT]
> **Zero Fabrication Policy**: The `/media` edge alone **does not** return analytics or insights (`views`, `reach`, `saved`, `shares`, `total_interactions`). Woka **never** fabricates views (e.g. by multiplying likes). Views and engagement metrics are only populated when explicitly queried from the `{media_id}/insights` edge or when an analysis job is executed.

---

## 3. Workflow Boundaries Across Meta Endpoints

A complete creator workflow spans distinct Meta Graph API edges, each requiring specific permissions:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      Meta Instagram Graph API                          │
└──────────────┬───────────────────┬───────────────────┬─────────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
      Profile Identity        Media Listing      Media Insights
     GET /v21.0/me           GET /{id}/media   GET /{id}/insights
               │                   │                   │
   - username, name        - id, caption       - views, reach
   - profile_pic_url       - media_type        - saved, shares
   - account_type          - media_url         - total_interactions
   - followers_count       - permalink                 │
               │                   │                   │
   [instagram_business_    [instagram_business_ [instagram_business_
          basic]                  basic]         manage_insights]
```

### Endpoint Matrix
1. **Account Identity**: `GET https://graph.instagram.com/{version}/me?fields=id,username,name,profile_picture_url,account_type`
   - *Permission*: `instagram_business_basic`
2. **Media Collection (Source of Truth)**: `GET https://graph.instagram.com/{version}/{user_id}/media?fields=id,caption,media_type,media_url,permalink,timestamp`
   - *Permission*: `instagram_business_basic`
3. **Reel Performance Insights**: `GET https://graph.instagram.com/{version}/{media_id}/insights?metric=views,reach,saved,shares,total_interactions`
   - *Permission*: `instagram_business_manage_insights`
4. **Compliance Callbacks**:
   - Deauthorization: `POST /api/v1/instagram/deauthorize` (parses `signed_request`)
   - Data Deletion: `POST /api/v1/instagram/data-deletion` (parses `signed_request`, wipes account data, returns tracking code)

---

## 4. FastAPI Backend Implementation

### 4.1 Service Layer (`backend/app/services/instagram_service.py`)
```python
def fetch_instagram_media_list(
    access_token: str,
    user_id: Optional[str] = None,
    fields: Optional[str] = None,
    limit: int = 25,
    max_pages: int = 2
) -> list:
    """
    Fetches media items (Reels/Videos) for the authenticated account with pagination support.
    Supports querying specific user_id (e.g. 17841458643277126) or default 'me'.
    Falls back to verified core cURL fields if extended fields are rejected (Meta code 100).
    """
```

### 4.2 Error Handling & Resilience
- **Error Code 190 / 102**: Maps to `MetaTokenExpiredError`. Automatically resets `account.is_connected = False` and prompts reauthorization.
- **Error Code 10 / 200**: Maps to `MetaPermissionError`. Triggered when user denies optional permissions.
- **Error Code 17 / 4 / 32**: Maps to `MetaRateLimitError`. Propagates HTTP 429 to client.
- **Error Code 100**: Extended field rejection (e.g. `like_count` unpermitted). Automatically falls back to verified cURL fields: `id,caption,media_type,media_url,permalink,timestamp`.
- **Transient 500 / Network Timeout**: Protected by exponential backoff retry via `_request_with_retry`.

### 4.3 API Router Endpoints (`backend/app/routers/instagram.py`)
- `GET /api/v1/instagram/media`: Authenticated endpoint to list connected media items.
- `GET /api/v1/instagram/status`: Returns connection state, token expiry, and granted permissions.
- `GET /api/v1/reel-intelligence/connected-reels`: Returns candidate Reels for 1-click analysis.

---

## 5. Security & Cryptographic Storage

1. **Token Encryption at Rest**:
   All access tokens are encrypted with AES-256 Fernet using `TOKEN_ENCRYPTION_KEY` before database persistence. Plaintext tokens never appear in database dumps or logs.
2. **OAuth State Verification**:
   OAuth `state` uses HMAC-SHA256 signatures with single-use UUID nonces and a 900-second expiration window to prevent CSRF and replay attacks.
3. **Tenant Scoping**:
   All endpoints strictly scope queries by `workspace_id` derived from the authenticated JWT session.
