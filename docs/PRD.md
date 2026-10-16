# Woka Reel Intelligence — Product Requirements Document (PRD)

## 1. Product Vision & Goals

**Woka Reel Intelligence** is an enterprise-grade AI analytics and creative intelligence platform for short-form video creators, agencies, and performance marketing teams. It combines computer vision, scene segmentation, acoustic cadence analysis, and verified Meta Graph API insights into actionable, explainable creative recommendations.

### Core Problems Solved:
1. **The Retention Drop Mystery:** Creators know viewers drop off, but cannot pinpoint the exact millisecond where pacing dragged, subtitles became unreadable, or visual monotony caused viewer swipe-away.
2. **Subjective Advice vs. Deterministic Signal:** Generic conversational AI gives platitudes ("make your hook catchier"). Woka Reel Intelligence provides mathematical metrics (WPM cadence, cut density, 9:16 safe-zone overlap, curiosity triggers).
3. **Data Integrity & Zero Fabricated Curves:** Where platforms do not expose private second-by-second viewer drop-off, Woka explicitly labels observations as creative heuristics rather than inventing synthetic retention curves.

---

## 2. User Personas

1. **Short-Form Content Creators:** Solo creators producing 3–10 Reels weekly, seeking higher reach and engagement velocity.
2. **Social Media Agencies & Editors:** Video teams needing objective editing notes, safe-zone compliance checks, and comparative A/B analysis before publishing.
3. **Brand Influencer Marketers:** Brands evaluating sponsored creator content deliverables and validating historical engagement authenticity.

---

## 3. Analysis Modes

### Mode A: Public Reel Analyzer
- **Input:** Any valid public Instagram Reel URL (`instagram.com/reel/{code}/`) or uploaded video file (`.mp4`, `.mov`, `.webm` up to 100MB).
- **Processing:** Video container inspection, OpenCV frame sampling, scene cut detection, WPM cadence, dead-air interval detection, OCR text reading, safe-zone compliance.
- **Analytics:** Public engagement metrics (Likes, Comments, Public Views where available).
- **Disclosures:** Discloses that private metrics (unique reach, saves, retention ratio) require Meta account authorization.

### Mode B: Connected Account Analyzer
- **Input:** Published Reels from an authenticated Instagram Professional (Creator/Business) account.
- **Processing:** Full video processing pipeline + authorized Meta Graph API insight ingestion.
- **Analytics:** Verified Unique Reach, Shares, Saves, Average Watch Time, Total Watch Time, Attributed Follows, Profile Visits, and Account Baseline Deltas.

---

## 4. Key Functional Features

1. **Multi-Stage Analysis Stepper:** Real-time visibility into pipeline stages (`QUEUED` $\to$ `INGESTING` $\to$ `PROCESSING_VIDEO` $\to$ `ANALYZING_METRICS` $\to$ `GENERATING_AI_REPORT` $\to$ `COMPLETED`).
2. **Eight Explainable Score Dimensions:**
   - Creative Quality Score (0–100)
   - Hook Strength Score (0–100)
   - Editing & Pacing Score (0–100)
   - Content Clarity Score (0–100)
   - CTA Effectiveness Score (0–100)
   - Performance Insights Score (0–100)
   - Growth & Conversion Opportunities Score (0–100)
   - Estimated Viral Potential (0–100, heuristic estimate)
3. **Timestamped Video Findings Timeline:** Millisecond-accurate findings categorizing creative strengths and retention hazards across `HOOK`, `PACING`, `VISUAL_CLARITY`, `AUDIO_SPEECH`, `SUBTITLES`, `STRUCTURE`, and `CTA`.
4. **Prioritized 3-Tier Action Plan:** What worked, what underperformed, why it happened, evidence from media, what to change, how to implement, and follow-up test metric.
5. **Creative Experiments Studio:** 4 proven hook frameworks, thumbnail directions, caption variations, and revised scripts.
6. **Multi-Reel Comparison Studio:** Side-by-side comparative analysis of 2 to 5 Reels with winner identification and key takeaways.
7. **Report Archive & History:** Filterable by date, account, analysis mode, and search keyword.

---

## 5. Non-Functional & Security Requirements

- **Zero-Hallucination Policy:** Never invent private Graph API metrics or viewer retention curves.
- **SSRF Protection:** Strict validation of URL destinations blocking access to internal or private IP ranges.
- **Binary Magic Bytes Validation:** Verify video streams at the byte level and reject disguised executables.
- **Token Security:** Meta Page Access Tokens encrypted with AES-256 at rest; never transmitted to the browser.
- **Performance Budget:** End-to-end processing under 15 seconds for 30-second video assets.
