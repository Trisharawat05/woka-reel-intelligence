# Woka Reel Intelligence — Architectural Specification & Production Guide

## 1. Executive Summary & Objective

**Woka Reel Intelligence** is an enterprise-grade AI analytics and creative intelligence platform for short-form video creators and performance marketing teams. It bridges the gap between raw video perception (computer vision, scene segmentation, audio dynamics, subtitle pacing) and verifiable performance telemetry (Meta Graph API authorized insights).

Rather than serving generic conversational feedback, Woka Reel Intelligence performs a multi-stage structural evaluation across four rigorous dimensions:
1. **Creative Quality Score (0–100):** Hook retention, visual pacing, audio cadence, subtitle synchronization, safe-zone compliance.
2. **Performance Score (0–100):** Engagement efficiency, like/comment velocity, shareability, and save bookmarks.
3. **Growth Conversion Score (0–100):** Follow-through attribution, profile visits, and call-to-action efficacy.
4. **Viral Potential Estimate (0–100):** Outlier probability based on distribution velocity relative to creator historical baselines.

---

## 2. Dual-Mode Architecture

| Feature Dimension | Mode A: Public Reel Analyzer | Mode B: Connected Account Analyzer |
|---|---|---|
| **Input Mechanism** | Public Instagram Reel URL or Direct Video Upload (`.mp4`, `.mov`, `.webm` up to 100MB) | Authorized Instagram Professional (Creator/Business) Account selection |
| **Authentication Scope** | Session JWT only; no Meta account required | Meta OAuth 2.0 with `instagram_basic`, `pages_show_list`, `pages_read_engagement` |
| **Video Intelligence** | Full OpenCV visual processing, PIL scene analysis, audio cadence, speech WPM, safe-zone check | Full video processing on authorized media URL |
| **Performance Data** | Visible engagement counts (Likes, Comments, Plays/Views where public) | Verified API Insights: Reach, Saves, Shares, Avg Watch Time, Attributed Follows |
| **Baseline Comparisons** | Workspace historical benchmark when available | Account-level historical 90-day distribution baseline & standard deviation |
| **Zero-Hallucination Policy** | Private retention curves & attributed reach are explicitly omitted with disclaimers | Private metrics are displayed with Meta API provenance and confidence ratings |

---

## 3. Video Intelligence Pipeline Architecture

```mermaid
flowchart TD
    Ingest[Reel Submission / Upload] --> IngestStage[Stage 1: Media Ingestion & Validation]
    IngestStage --> VideoProc[Stage 2: OpenCV & PIL Video Processor]
    IngestStage --> AudioProc[Stage 2: Audio & Cadence Processor]
    
    subgraph VideoEngine [Visual Perception]
        VideoProc --> AspectCheck[9:16 Aspect Ratio & Framing Check]
        VideoProc --> SafeZone[Instagram Overlay Safe-Zone Hazard Detector]
        VideoProc --> SceneCuts[Histogram Correlation Scene Cut Detector]
        VideoProc --> Lighting[Perceived Luminance & Contrast Variance]
        VideoProc --> Pacing[Static Shot & Cut Frequency Pacing Engine]
    end
    
    subgraph AudioEngine [Acoustic & Timing Perception]
        AudioProc --> WPM[Words Per Minute & Cadence Tracker]
        AudioProc --> DeadAir[Dead-Air / Silence Threshold (>1.2s)]
        AudioProc --> Sync[Subtitle-to-Audio Synchronicity]
    end
    
    VideoEngine --> AnalyticsStage[Stage 3: Performance Metric Engine]
    AudioEngine --> AnalyticsStage
    AnalyticsStage --> ScoringStage[Stage 4: 4-Tier Scoring & AI Diagnosis]
    ScoringStage --> Persist[Stage 5: Report Persistence & Cache Invalidation]
```

### 3.1 Visual Perception Engine
- **Safe-Zone Compliance:** Instagram overlays icons (profile, like, comment, share, audio ticker) at the right edge (right 18%) and lower footer (bottom 22%). Text and critical subjects detected in these coordinates trigger a `VISUAL_CLARITY` hazard.
- **Scene Cut Detection:** Consecutive frames are compared using 3-channel RGB normalized cross-correlation histograms ($\Delta \chi^2 > 0.42$). Cut density per minute is benchmarked against optimal short-form pacing (12–24 cuts/min).
- **Static Frame Warning:** Continuous visual stagnation exceeding 3.5 seconds flags a retention drop hazard.

### 3.2 Acoustic Perception Engine
- **Cadence & WPM:** Natural conversational cadence is scored between 135–175 WPM. Rates under 115 WPM trigger pacing lag warnings; rates above 195 WPM trigger comprehension fatigue warnings.
- **Dead-Air Detection:** Audio pauses exceeding 1,200ms without background audio beds are flagged with millisecond timestamps for trimming.

---

## 4. Calculated Performance Metrics

All metrics follow strict mathematical formulas with documented numerators, denominators, and limitation labels:

$$\text{Engagement Rate} = \frac{\text{Likes} + \text{Comments} + \text{Shares} + \text{Saves}}{\max(\text{Views}, 1)}$$

$$\text{Share-to-View Ratio} = \frac{\text{Shares}}{\max(\text{Views}, 1)} \times 100\%$$

$$\text{Save-to-View Ratio} = \frac{\text{Saves}}{\max(\text{Views}, 1)} \times 100\%$$

$$\text{Watch Ratio} = \frac{\text{Average Watch Time}}{\text{Total Video Duration}}$$

$$\text{Baseline Delta} = \frac{\text{Reel Views} - \text{Creator Median Views}}{\text{Creator Median Views}} \times 100\%$$

---

## 5. AI Diagnosis & Scoring Methodology

### 5.1 Creative Quality Score (Weight: 100%)
- **Hook Effectiveness (30%):** Visual contrast change within 0–3s, spoken hook punchiness, curiosity gap.
- **Visual Pacing & Dynamics (25%):** Cut frequency, static shot duration, safe-zone clearance.
- **Audio & Delivery (25%):** Speech tempo (WPM), dead-air absence, soundbed clarity.
- **Structure & CTA (20%):** Value delivery payoff, clear call-to-action at closing 15%.

### 5.2 Performance Score (Weight: 100%)
- **Engagement Depth (35%):** Saves (high intent) and Shares (viral coefficient).
- **Conversation Density (25%):** Comment rate relative to reach.
- **View Velocity (25%):** Performance vs. historical median.
- **Consumption Ratio (15%):** Average watch-time-to-duration ratio.

### 5.3 Growth Conversion Score (Weight: 100%)
- Attributable follows per 1,000 views.
- Profile visit rate.
- Frictionless CTA clarity (e.g. comment automation keyword triggers).

### 5.4 Viral Potential Estimate (0–100)
- Derived from share velocity ($S_v$), initial watch ratio ($W_r$), and safe-zone visibility.

---

## 6. API Reference (`/api/v1/reel-intelligence`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/jobs/url` | Submit public Instagram Reel URL for async analysis | Bearer JWT |
| `POST` | `/jobs/upload` | Upload video file (`multipart/form-data`) for analysis | Bearer JWT |
| `POST` | `/jobs/connected` | Ingest and analyze connected Meta Instagram Reel | Bearer JWT |
| `GET` | `/jobs/{job_id}` | Poll real-time progress (0–100%) and stage status | Bearer JWT |
| `GET` | `/reports/{report_id}` | Retrieve comprehensive finalized analysis report | Bearer JWT |
| `GET` | `/reports` | List paginated reports for active workspace | Bearer JWT |
| `POST` | `/compare` | Generate comparative matrix across 2 to 5 reports | Bearer JWT |
| `POST` | `/jobs/{job_id}/retry` | Retry failed analysis job with exponential backoff | Bearer JWT |
| `GET` | `/connected-reels` | List authorized Instagram account Reels | Bearer JWT |
| `GET` | `/thumbnails/{file}` | Serve generated thumbnail previews | Public / Authenticated |

---

## 7. Security, Privacy & Zero-Hallucination Guardrails

1. **Multi-Tenant Isolation:** All jobs, media assets, metric snapshots, reports, and comparisons enforce `workspace_id` scoping at the database query level.
2. **Access Token Protection:** Meta Page Access Tokens are encrypted with AES-256 before storage in `instagram_accounts` and never transmitted to the frontend client.
3. **Zero Fabricated Curves:** Where Meta does not supply second-by-second drop-off retention curves, the UI explicitly flags timeline findings as heuristic observations rather than pretending to display empirical viewer drop-off.
4. **Media Retention:** Ingested media files and extracted frames are isolated under `backend/storage/uploads/` and protected by MIME validation and path traversal sanitization.
