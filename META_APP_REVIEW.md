# WOKA — Meta App Review Submission & Reviewer Walkthrough Guide

**Document Version:** 1.0  
**Target Platform:** Official Meta Graph API / Instagram Graph API v19.0+  
**Target Application:** Woka (Creator SaaS & Instagram Comment-to-DM Platform)  
**Submission Status:** Pre-Submission Verification & Staging Validation Complete  

---

## 1. Application Overview

**Woka** is a creator growth and automation platform designed specifically for Instagram creators, influencers, and brands. Woka automates engagement by detecting permitted keyword comments on a creator's public Instagram posts or reels and delivering tailored Direct Messages (such as product links, discounts, free e-books, or guides) directly to fans.

---

## 2. Permissions Requested & Business Justification

| Permission | Category | User Facing Feature | Official Justification |
|---|---|---|---|
| `instagram_basic` | User Info & Media | Connected Account Status & Profile Sync | Allows the creator to view their linked profile information, follower counts, and public media within the Woka workspace. |
| `instagram_manage_comments` | Engagement / Webhooks | Inbound Comment Listening | Subscribes Woka to official Meta Webhook comment events on creator posts, allowing Woka to match keywords specified by the creator. |
| `instagram_manage_messages` | Messaging / Direct Messages | Automated Direct Message Dispatch | Enables Woka to send a one-time direct message response containing requested links or resources to fans who comment with matching keywords. |
| `pages_show_list` | Facebook Page Binding | Account Discovery | Discovers Facebook Pages connected to the creator's Instagram Professional/Creator account during OAuth onboarding. |
| `pages_read_engagement` | Analytics & Validation | Engagement Metrics | Enables reading aggregate post metrics to calculate creator engagement rates and audience insights. |

---

## 3. Meta App Reviewer Test Account & Credentials

To enable Meta app reviewers to test Woka in a controlled environment without requiring live personal Instagram accounts:

- **Reviewer Testing URL:** `https://staging.woka.local:8443` or `https://app.woka.io`
- **Reviewer Demo Credentials:**
  - **Email:** `meta-reviewer@woka.io`
  - **Password:** `MetaReviewer2026!`
  - **Role:** `CREATOR`
- **Pre-Configured Test Instagram Account:**
  - **Username:** `@creator_woka_demo`
  - **Account Type:** Instagram Creator Account
  - **Linked Facebook Page:** Woka Creator Testing Page

---

## 4. Step-by-Step Reviewer Walkthrough & Demonstration

### Step 1: Creator Authentication
1. Navigate to the login page at `/login`.
2. Enter the reviewer credentials and click **Sign In**.
3. You will be redirected to the main Woka Dashboard.

### Step 2: Instagram Account Connection
1. In the sidebar, click on **Instagram Account** (`/dashboard/instagram`).
2. Click **Connect Instagram Account** (or toggling the Sandbox Testing environment).
3. Meta OAuth dialog opens requesting approval for `instagram_basic`, `instagram_manage_comments`, and `instagram_manage_messages`.
4. Grant the requested permissions.
5. The Woka dashboard displays the connected Instagram profile with follower count and active connection status.

### Step 3: Setting Up a Comment-to-DM Automation
1. In the sidebar, click on **Automations** (`/dashboard/automations`).
2. Click **Create Automation**.
3. Enter rule details:
   - **Name:** "Guide Lead Magnet"
   - **Trigger:** "When someone comments on any post"
   - **Trigger Keywords:** `guide`, `ebook`, `free`
   - **Match Condition:** "Contains any keyword"
   - **DM Message Template:** "Hi {{username}}, here is your free guide: https://woka.io/creator-guide"
   - **Anti-Spam Cooldown:** 60 minutes
4. Click **Save Automation**. The rule is active.

### Step 4: Webhook Event Ingestion & Message Dispatch
1. Reviewers can test via the built-in **Interactive Automation Simulator** or by posting a comment on a test reel.
2. In the simulator:
   - Enter Comment Text: *"Please send me the free guide!"*
   - Author: `@creative_reviewer`
   - Click **Run Test Simulation**.
3. Reviewer sees:
   - Match status: `SIMULATION_SUCCESS`
   - Matched keyword: `guide`
   - Dispatched DM preview: *"Hi @creative_reviewer, here is your free guide: https://woka.io/creator-guide"*
   - Execution audit log recorded in the history table.

### Step 5: Anti-Spam Policy Enforcement
1. Submit a second comment from the same username immediately.
2. The automation engine suppresses duplicate messaging with status `SUPPRESSED_COOLDOWN` / `RATE_LIMITED` to prevent unsolicited spamming.

---

## 5. Screen Recording Video Script

A 3-minute video recording (`woka_meta_reviewer_walkthrough.mp4`) has been recorded following this script:

- **0:00 - 0:30:** Introduction to Woka value proposition and UI overview.
- **0:30 - 1:15:** Connecting Instagram via official Meta OAuth dialog, showing granular permission toggles.
- **1:15 - 2:00:** Creating a Comment-to-DM automation rule with anti-spam cooldown and message templates.
- **2:00 - 2:40:** Inbound comment trigger and outbound automated DM delivery demonstration.
- **2:40 - 3:00:** Review of Privacy Policy, Terms of Service, and Data Deletion instructions.

---

## 6. Data Deletion & Privacy Policy Compliance

- **Privacy Policy URL:** `https://app.woka.io/privacy`
- **Terms of Service URL:** `https://app.woka.io/terms`
- **Data Deletion Callback Endpoint:**
  - `POST https://api.woka.io/api/v1/instagram/data-deletion`
  - Validates `signed_request` with `META_APP_SECRET`.
  - Clears stored OAuth tokens and disconnects account.
  - Returns `{"url": "https://app.woka.io/deletion-status?code=...", "confirmation_code": "..."}`.
- **Deauthorize Callback Endpoint:**
  - `POST https://api.woka.io/api/v1/instagram/deauthorize`
  - Immediately invalidates stored tokens upon permission revocation.
