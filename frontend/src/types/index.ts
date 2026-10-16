export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "CREATOR" | "BRAND" | "AGENCY" | "ADMIN";
  avatar_url?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
}

export interface InstagramAccount {
  id: string;
  workspace_id: string;
  ig_user_id: string;
  username: string;
  name?: string;
  profile_pic_url?: string;
  is_connected: boolean;
  is_sandbox: boolean;
  followers_count: number;
  media_count: number;
  token_expires_at?: string;
  created_at: string;
}

export interface Automation {
  id: string;
  workspace_id: string;
  ig_account_id: string;
  name: string;
  trigger_type: string;
  target_post_type: string;
  target_post_id?: string;
  target_post_preview_url?: string;
  match_type: string;
  trigger_keywords: string[];
  dm_message_template: string;
  reply_comment_template?: string;
  is_active: boolean;
  cooldown_minutes: number;
  total_triggered_count: number;
  created_at: string;
}

export interface AutomationLog {
  id: string;
  automation_id: string;
  automation_name?: string;
  recipient_ig_id: string;
  recipient_username: string;
  trigger_comment_id?: string;
  trigger_comment_text?: string;
  dm_text_sent: string;
  status: "SUCCESS" | "PENDING" | "RATE_LIMITED" | "FAILED" | "SIMULATED";
  error_message?: string;
  created_at: string;
}

export interface AnalyticsSummary {
  followers_count: number;
  followers_growth_30d: number;
  following_count: number;
  media_count: number;
  reach_30d: number;
  impressions_30d: number;
  avg_engagement_rate: number;
  is_sandbox: boolean;
}

export interface AnalyticsTimeSeriesPoint {
  date: string;
  followers: number;
  reach: number;
  impressions: number;
  engagement_rate: number;
}

export interface TopPost {
  id: string;
  media_url: string;
  permalink: string;
  caption: string;
  like_count: number;
  comments_count: number;
  reach: number;
  engagement_rate: number;
  published_at: string;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  time_series: AnalyticsTimeSeriesPoint[];
  demographics: {
    age_distribution: Record<string, number>;
    gender_distribution: Record<string, number>;
    top_countries: Record<string, number>;
    top_cities: Record<string, number>;
  };
  top_posts: TopPost[];
}

export interface CreatorProfile {
  id: string;
  workspace_id: string;
  slug: string;
  display_name: string;
  bio?: string;
  avatar_url?: string;
  niches: string[];
  location?: string;
  rate_reel: number;
  rate_story: number;
  rate_bundle: number;
  is_verified: boolean;
  is_public: boolean;
  followers_count: number;
  engagement_rate: number;
  total_reach_30d: number;
}

export interface BrandCampaign {
  id: string;
  brand_workspace_id: string;
  title: string;
  description: string;
  niche: string;
  budget_min: number;
  budget_max: number;
  required_deliverables: string[];
  submission_deadline: string;
  status: string;
  created_at: string;
  brand_name?: string;
  applications_count?: number;
}

export interface CampaignApplication {
  id: string;
  campaign_id: string;
  creator_workspace_id: string;
  creator_name?: string;
  pitch_text: string;
  proposed_rate: number;
  status: "APPLIED" | "ACCEPTED" | "REJECTED" | "COMPLETED";
  created_at: string;
  campaign_title?: string;
}

export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface Invoice {
  id: string;
  workspace_id: string;
  invoice_number: string;
  client_name: string;
  client_email: string;
  total_amount: number;
  currency: string;
  status: "DRAFT" | "SENT" | "PAID" | "OVERDUE" | "CANCELLED";
  due_date: string;
  line_items: InvoiceLineItem[];
  notes?: string;
  created_at: string;
}

export interface Subscription {
  plan_tier: "FREE" | "PRO" | "AGENCY";
  status: string;
  dm_limit_monthly: number;
  dm_used_monthly: number;
  ai_limit_monthly: number;
  ai_used_monthly: number;
  current_period_end: string;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  title: string;
  message: string;
  category: "AUTOMATION" | "CAMPAIGN" | "INVOICE" | "SYSTEM";
  link?: string;
  is_read: boolean;
  created_at: string;
}

export interface ReelAnalysisJob {
  id: string;
  workspace_id: string;
  analysis_mode: "PUBLIC_URL" | "VIDEO_UPLOAD" | "CONNECTED_ACCOUNT";
  input_type: "url" | "upload" | "connected_account";
  status: "QUEUED" | "INGESTING" | "PROCESSING_VIDEO" | "ANALYZING_METRICS" | "GENERATING_AI_REPORT" | "COMPLETED" | "FAILED";
  progress_percent: number;
  stage_message: string;
  error_message?: string;
  source_url?: string;
  source_media_id?: string;
  report_id?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface MetricItem {
  name: string;
  value: number | null;
  formatted: string;
  numerator: string;
  denominator: string;
  time_window: string;
  source: string;
  benchmark?: string;
  benchmark_status: "ABOVE_AVERAGE" | "AVERAGE" | "BELOW_AVERAGE" | "N/A";
  limitations: string;
}

export interface ScoreComponent {
  name: string;
  score: number;
  weight: number;
  status: "EXCELLENT" | "GOOD" | "NEEDS_IMPROVEMENT" | "POOR";
  details: string;
}

export interface ScoreDetail {
  score: number;
  rating: "EXCEPTIONAL" | "STRONG" | "MODERATE" | "UNDERPERFORMING";
  confidence: number;
  methodology: string;
  components: ScoreComponent[];
  evidence_summary: string;
}

export interface ScoreOverview {
  creative_quality: ScoreDetail;
  performance: ScoreDetail;
  growth_conversion: ScoreDetail;
  viral_potential: ScoreDetail;
}

export interface TimelineFinding {
  id: string;
  timestamp_start_seconds: number;
  timestamp_end_seconds: number;
  time_range_formatted: string;
  category: "HOOK" | "PACING" | "VISUAL_CLARITY" | "AUDIO_SPEECH" | "SUBTITLES" | "STRUCTURE" | "CTA";
  severity: "CRITICAL" | "WARNING" | "OPPORTUNITY" | "STRENGTH";
  observation: string;
  evidence: string;
  recommendation: string;
  proposed_edit: string;
  is_heuristic_risk: boolean;
}

export interface ActionPlanItem {
  priority: number;
  area: string;
  what_worked: string;
  what_underperformed: string;
  why_it_happened: string;
  supporting_evidence: string;
  what_to_change: string;
  how_to_implement: string;
  follow_up_test_metric: string;
}

export interface CreativeAlternatives {
  alternative_hooks: Array<{ framework: string; hook_text: string; reasoning: string }>;
  thumbnail_concepts: Array<{ visual_direction: string; overlay_text: string; focal_point: string }>;
  caption_suggestions: Array<{ variation_name: string; text: string; suggested_hashtags: string }>;
  cta_variations: Array<{ type: string; cta_text: string }>;
  revised_script: {
    hook: string;
    body: string;
    payoff: string;
    cta: string;
    shot_notes: string;
  };
}

export interface ReelReport {
  id: string;
  workspace_id: string;
  job_id: string;
  title: string;
  caption?: string;
  analysis_mode: "PUBLIC_URL" | "VIDEO_UPLOAD" | "CONNECTED_ACCOUNT";
  thumbnail_url?: string;
  duration_seconds: number;
  scores: ScoreOverview;
  creative_quality_score?: number;
  performance_score?: number;
  growth_conversion_score?: number;
  viral_potential_estimate?: number;
  calculated_metrics: Record<string, MetricItem>;
  video_intelligence: Record<string, any>;
  timeline_findings: TimelineFinding[];
  prioritized_action_plan: ActionPlanItem[];
  creative_alternatives: CreativeAlternatives;
  provenance: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ReelReportSummary {
  id: string;
  workspace_id: string;
  job_id: string;
  title: string;
  analysis_mode: "PUBLIC_URL" | "VIDEO_UPLOAD" | "CONNECTED_ACCOUNT";
  thumbnail_url?: string;
  duration_seconds: number;
  creative_quality_score: number;
  performance_score: number;
  growth_conversion_score: number;
  viral_potential_estimate: number;
  views_count: number;
  likes_count: number;
  engagement_rate: number;
  created_at: string;
}

export interface ReelComparison {
  id: string;
  workspace_id: string;
  report_ids: string[];
  reports: ReelReport[];
  comparison_matrix: Record<string, any>;
  comparative_takeaways: string[];
  winner_id?: string;
  created_at: string;
}

