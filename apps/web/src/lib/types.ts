// TS mirror schematów backendu (apps/api/app/schemas.py)

export type Brand = "salespros" | "gawronify" | "other";

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
  bookings: number;
  sales: number;
  ig_sync_ghosts: number;
  daily_trend: TrendPoint[];
  last_updated_iso: string;
  data_source: string;
}

export interface CampaignRow {
  campaign_id: string;
  name: string;
  brand: Brand;
  status: string;
  objective: string | null;
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
  hook_rate: number | null;
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
