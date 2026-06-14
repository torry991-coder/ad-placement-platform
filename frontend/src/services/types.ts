// ── Enums ────────────────────────────────────────────────────

export type BidStrategy =
  | "max_conversions"
  | "target_cpa"
  | "target_roas"
  | "enhanced_cpc"
  | "manual_cpc";

export type CampaignStatus = "draft" | "active" | "paused" | "learning" | "ended";

export type AdGroupStatus = "active" | "paused" | "removed";

export type ExperimentType = "ab_test" | "multivariate" | "bandit";

export type ExperimentStatus = "draft" | "running" | "completed" | "stopped";

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertAction = "notify" | "pause_campaign" | "reduce_budget";

export type CreativeType = "text" | "image" | "video" | "responsive" | "html5";

// ── Campaign ─────────────────────────────────────────────────

export interface Campaign {
  id: number;
  name: string;
  status: CampaignStatus;
  daily_budget: number;
  total_budget?: number | null;
  bid_strategy: BidStrategy;
  target_cpa?: number | null;
  target_roas?: number | null;
  max_cpc?: number | null;
  start_date: string; // ISO datetime
  end_date?: string | null;
  platforms?: string[] | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  name: string;
  daily_budget: number;
  total_budget?: number | null;
  bid_strategy?: BidStrategy;
  target_cpa?: number | null;
  target_roas?: number | null;
  max_cpc?: number | null;
  start_date: string;
  end_date?: string | null;
  platforms?: string[];
  notes?: string | null;
}

export interface CampaignUpdate {
  name?: string | null;
  status?: CampaignStatus | null;
  daily_budget?: number | null;
  total_budget?: number | null;
  bid_strategy?: BidStrategy | null;
  target_cpa?: number | null;
  target_roas?: number | null;
  max_cpc?: number | null;
  end_date?: string | null;
  notes?: string | null;
}

// ── AdGroup ──────────────────────────────────────────────────

export interface AdGroup {
  id: number;
  campaign_id: number;
  name: string;
  status: AdGroupStatus;
  bid_strategy_override?: string | null;
  max_cpc?: number | null;
  target_cpa?: number | null;
  age_range?: number[] | null;
  gender?: string | null;
  devices?: string[] | null;
  regions?: string[] | null;
  interests?: string[] | null;
  keywords?: string[] | null;
  created_at: string;
  updated_at: string;
}

// ── Creative ─────────────────────────────────────────────────

export interface Creative {
  id: number;
  ad_group_id: number;
  name: string;
  creative_type: CreativeType;
  headline?: string | null;
  description?: string | null;
  call_to_action?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  landing_url?: string | null;
  ctr: number;
  cvr: number;
  fatigue_score: number;
  is_active: boolean;
  last_shown_at?: string | null;
  created_at: string;
  updated_at: string;
}

// ── Performance ──────────────────────────────────────────────

export interface PerformanceMetric {
  id: number;
  campaign_id: number;
  date: string;
  hour?: number | null;
  platform?: string | null;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  ctr?: number | null;
  cvr?: number | null;
  cpc?: number | null;
  cpa?: number | null;
  roas?: number | null;
  quality_score?: number | null;
  bounce_rate?: number | null;
  created_at: string;
}

// ── Experiment ───────────────────────────────────────────────

export interface Experiment {
  id: number;
  name: string;
  experiment_type: ExperimentType;
  status: ExperimentStatus;
  control_campaign_id: number;
  variant_campaign_id: number;
  traffic_split: number;
  results?: Record<string, unknown> | null;
  is_significant: boolean;
  confidence_level?: number | null;
  winner_variant?: string | null;
  start_date: string;
  end_date?: string | null;
  auto_stop: boolean;
  hypothesis?: string | null;
  created_at: string;
  updated_at: string;
}

// ── Alert ────────────────────────────────────────────────────

export interface AlertRule {
  id: number;
  name: string;
  is_enabled: boolean;
  condition: Record<string, unknown>;
  severity: AlertSeverity;
  action: AlertAction;
  scope_type: string;
  scope_id?: number | null;
  notify_channels?: string[] | null;
  webhook_url?: string | null;
  cooldown_minutes: number;
  last_triggered_at?: string | null;
  trigger_count: number;
  created_at: string;
  updated_at: string;
}

// ── Audience ─────────────────────────────────────────────────

export interface AudienceSegment {
  id: number;
  name: string;
  description?: string | null;
  rules: Record<string, unknown>;
  member_count: number;
  avg_ctr: number;
  avg_cvr: number;
  roas: number;
  seed_audience_id?: number | null;
  labels?: string[] | null;
  created_at: string;
  updated_at: string;
}

// ── Bidding ──────────────────────────────────────────────────

export interface AuctionRequest {
  campaign_id: number;
  ad_group_id: number;
  daily_budget: number;
  budget_spent_today?: number;
  bid_strategy?: string;
  target_cpa?: number | null;
  target_roas?: number | null;
  max_cpc?: number | null;
  age_range?: number[] | null;
  gender?: string | null;
  device?: string;
  platform?: string;
  hour?: number | null;
}

export interface AuctionResponse {
  bid_amount: number;
  predicted_ctr: number;
  predicted_cvr: number;
  ad_rank: number;
  won: boolean;
  win_price: number;
  estimated_conversion_value: number;
  model_used: string;
}

export interface BatchAuctionResponse {
  results: AuctionResponse[];
  total_auctions: number;
  won_count: number;
  total_cost: number;
}

// ── Dashboard ────────────────────────────────────────────────

export interface DashboardKPI {
  active_campaigns: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_spend: number;
  total_revenue: number;
  avg_ctr: number;
  avg_cvr: number;
  avg_roas: number;
  budget_utilization: number;
  alert_count: number;
}

// ── Agent ────────────────────────────────────────────────────

export interface AgentChatRequest {
  message: string;
  campaign_id?: number | null;
  context?: Record<string, unknown> | null;
}

export interface AgentChatResponse {
  reply: string;
  actions: Record<string, unknown>[];
  suggestions: string[];
  model_used: string;
}

// ── Paginated response ───────────────────────────────────────

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  offset: number;
  limit: number;
}
