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
