// TS mirror schematów backendu (apps/api/app/schemas.py)

export type Brand = "salespros" | "gawronify" | "other";

export type CampaignType = "acquisition" | "retarget" | "unknown";

export interface CplSplit {
  spend_acquisition: number;
  spend_retarget: number;
  spend_unknown: number;
  leads_acquisition: number;
  leads_retarget: number;
  leads_unknown: number;
  cpl_acquisition: number | null;
  cpl_retarget: number | null;
  untagged_count: number;
  // CPA/ROAS split (sales-based)
  sales_acquisition: number;
  sales_retarget: number;
  revenue_acquisition: number;
  revenue_retarget: number;
  cpa_acquisition: number | null;
  cpa_retarget: number | null;
  roas_acquisition: number | null;
  roas_retarget: number | null;
  // Retarget separation
  bookings_acquisition: number;
  bookings_retarget: number;
  re_engaged_leads_retarget: number;
  cost_per_booking_retarget: number | null;
}

export interface TrendPoint {
  date: string;
  spend: number;
  leads: number;
  real_cpl: number | null;
  bookings: number;
}

export interface OverviewResponse {
  from_: string;
  to: string;
  tz: string;
  spend: number;
  real_leads: number;
  meta_leads: number;
  real_cpl: number | null;
  meta_cpl: number | null;
  real_cpb: number | null;
  bookings: number;                  // kohort: leady dodane w okresie + booked
  bookings_in_period: number;        // flow: wszystkie spotkania ze startTime w okresie (ground truth)
  sales_in_period: number;           // flow: wszystkie sprzedaże (closing + CS pipeline) w okresie
  revenue_in_period: number;         // flow: revenue ze wszystkich sale opp w okresie
  sales: number;
  ig_sync_ghosts: number;
  daily_trend: TrendPoint[];
  last_updated_iso: string;
  data_source: string;
  split: CplSplit | null;
  revenue: number;
  cpa: number | null;
  roas: number | null;
  // Fix #A5: 3-bucket attribution
  utm_attributed_leads: number;      // mocna attribution per kreacja (paid + utmContent)
  paid_unmapped_leads: number;       // paid bez utmContent
  untrackable_leads: number;         // organic / direct / inne
}

export interface CampaignRow {
  campaign_id: string;
  name: string;
  brand: Brand;
  status: string;
  objective: string | null;
  campaign_type: CampaignType;
  is_manual_type: boolean;
  spend: number;
  impressions: number;
  ctr: number;
  cpm: number;
  frequency: number;
  meta_leads: number;
  ghl_leads: number;
  real_cpl: number | null;
  meta_cpl: number | null;
  bookings: number;
  sales: number;
  revenue: number;
  cpa: number | null;
  roas: number | null;
  daily_budget: number | null;
}

export interface CampaignsResponse {
  campaigns: CampaignRow[];
}

export interface AdsetRow {
  adset_id: string;
  name: string;
  parent_campaign_id: string;
  parent_campaign_name: string;
  brand: Brand;
  status: string;
  optimization_goal: string | null;
  spend: number;
  impressions: number;
  ctr: number;
  frequency: number;
  meta_leads: number;
  ghl_leads: number;
  real_cpl: number | null;
  bookings: number;
  sales: number;
  revenue: number;
  cpa: number | null;
  roas: number | null;
}

export interface AdsetsResponse {
  adsets: AdsetRow[];
}

export interface CreativeRow {
  ad_id: string;
  ad_name: string;
  campaign_name: string;
  brand: Brand;
  status: string;
  thumbnail_url: string | null;
  video_id: string | null;
  creative_title: string | null;
  creative_body: string | null;
  spend: number;
  impressions: number;
  ctr: number;
  cpm: number;
  frequency: number;
  meta_leads: number;
  ghl_leads: number;
  real_cpl: number | null;
  meta_cpl: number | null;
  bookings: number;
  sales: number;
  revenue: number;
  cpa: number | null;
  roas: number | null;
  hook_rate: number | null;        // 3-sec views / impressions
  hold_rate: number | null;        // 15-sec / 3-sec
  health_score: number | null;     // composite 0-100, null = za mało danych
  health_status: string;           // "winner" | "average" | "loser" | "insufficient"
  winner_badge: boolean;
  loser_badge: boolean;
}

export interface CreativesResponse {
  creatives: CreativeRow[];
  avg_real_cpl: number | null;
}

export interface CreativeContact {
  contact_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  date_added: string;
  booked: boolean;
  sold: boolean;
  ghl_url: string;
}

export interface CreativeDetailResponse {
  ad_id: string;
  ad_name: string;
  campaign_name: string;
  brand: Brand;
  creative: Record<string, unknown>;
  trend: TrendPoint[];
  leads: CreativeContact[];
}

export interface FunnelStage {
  stage_name: string;
  count: number;
  value_pln: number;
}

export interface FunnelDropoff {
  from_stage: string;
  to_stage: string;
  rate: number;
}

export interface FunnelResponse {
  pipeline_name: string;
  stages: FunnelStage[];
  dropoff: FunnelDropoff[];
}

export interface AdminCampaignRow {
  campaign_id: string;
  name: string;
  objective: string | null;
  status: string;
  spend_30d: number;
  campaign_type: CampaignType;
  is_manual: boolean;
  suggested_type: CampaignType;
}

export interface HistoricalPeriod {
  label: string;
  from_: string;
  to: string;
  spend: number;
  leads: number;
  cpl: number | null;
}

export interface HistoricalContextResponse {
  periods: HistoricalPeriod[];
  delta_cpl_vs_30d_pct: number | null;
  delta_cpl_vs_year_pct: number | null;
  generated_at: string;
}

export interface Insight {
  severity: "winner" | "warn" | "critical" | "info" | string;
  title: string;
  why: string;
  action: string;
  ad_id: string | null;
}

export interface AccountSummary {
  spend: number | null;
  real_leads: number | null;
  real_cpl: number | null;
  bookings: number | null;
  sales: number | null;
  revenue: number | null;
  roas: number | null;
}

export interface InsightsResponse {
  insights: Insight[];
  generated_at: string | null;
  stale: boolean;
  date: string | null;
  account_summary: AccountSummary | null;
  model: string | null;
}

export interface AdminCampaignsResponse {
  campaigns: AdminCampaignRow[];
  untagged_count: number;
}

export interface AdminSetTypeResponse {
  campaign_id: string;
  campaign_type: CampaignType;
  is_manual: boolean;
}
