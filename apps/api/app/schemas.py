"""Pydantic response schemas — mirror dla TypeScript types we frontendzie."""
from __future__ import annotations

from pydantic import BaseModel


class Brand:
    SALESPROS = "salespros"
    GAWRONIFY = "gawronify"
    OTHER = "other"


class TrendPoint(BaseModel):
    date: str
    spend: float
    leads: int
    real_cpl: float | None
    bookings: int


class CplSplit(BaseModel):
    spend_acquisition: float
    spend_retarget: float
    spend_unknown: float
    leads_acquisition: int
    leads_retarget: int
    leads_unknown: int
    cpl_acquisition: float | None
    cpl_retarget: float | None
    untagged_count: int  # ile kampanii ma campaign_type=="unknown" (do bannera)


class OverviewResponse(BaseModel):
    from_: str
    to: str
    tz: str
    spend: float
    real_leads: int
    meta_leads: int
    real_cpl: float | None
    meta_cpl: float | None
    real_cpb: float | None
    bookings: int
    sales: int
    ig_sync_ghosts: int
    daily_trend: list[TrendPoint]
    last_updated_iso: str
    data_source: str  # "live" | "snapshot"
    split: CplSplit | None = None

    model_config = {"populate_by_name": True}


class CampaignRow(BaseModel):
    campaign_id: str
    name: str
    brand: str
    status: str
    objective: str | None = None
    campaign_type: str = "unknown"  # acquisition | retarget | unknown
    is_manual_type: bool = False  # czy tag pochodzi z manual override (true) czy z auto-rules (false)
    spend: float
    impressions: int
    ctr: float
    cpm: float
    frequency: float
    meta_leads: int
    ghl_leads: int
    real_cpl: float | None
    meta_cpl: float | None
    bookings: int
    sales: int
    daily_budget: float | None = None


class CampaignsResponse(BaseModel):
    campaigns: list[CampaignRow]


class AdsetRow(BaseModel):
    adset_id: str
    name: str
    parent_campaign_id: str
    parent_campaign_name: str
    brand: str
    status: str
    optimization_goal: str | None = None
    spend: float
    impressions: int
    ctr: float
    frequency: float
    meta_leads: int
    ghl_leads: int
    real_cpl: float | None


class AdsetsResponse(BaseModel):
    adsets: list[AdsetRow]


class CreativeRow(BaseModel):
    ad_id: str
    ad_name: str
    campaign_name: str
    brand: str
    status: str
    thumbnail_url: str | None = None
    video_id: str | None = None
    creative_title: str | None = None
    creative_body: str | None = None
    spend: float
    impressions: int
    ctr: float
    cpm: float
    frequency: float
    meta_leads: int
    ghl_leads: int
    real_cpl: float | None
    meta_cpl: float | None
    bookings: int
    sales: int
    hook_rate: float | None = None  # video_p25 / impressions
    winner_badge: bool = False
    loser_badge: bool = False


class CreativesResponse(BaseModel):
    creatives: list[CreativeRow]
    avg_real_cpl: float | None


class CreativeContact(BaseModel):
    contact_id: str
    name: str
    email: str | None
    phone: str | None
    date_added: str
    booked: bool
    sold: bool
    ghl_url: str


class CreativeDetailResponse(BaseModel):
    ad_id: str
    ad_name: str
    campaign_name: str
    brand: str
    creative: dict  # raw creative JSON z Meta
    trend: list[TrendPoint]
    leads: list[CreativeContact]


class FunnelStage(BaseModel):
    stage_name: str
    count: int
    value_pln: float


class FunnelDropoff(BaseModel):
    from_stage: str
    to_stage: str
    rate: float


class FunnelResponse(BaseModel):
    pipeline_name: str
    stages: list[FunnelStage]
    dropoff: list[FunnelDropoff]


class RefreshResponse(BaseModel):
    invalidated_keys: int
    snapshot_triggered: bool


class AdminCampaignRow(BaseModel):
    campaign_id: str
    name: str
    objective: str | None = None
    status: str
    spend_30d: float
    campaign_type: str  # acquisition | retarget | unknown
    is_manual: bool  # czy aktualnie z manual override
    suggested_type: str  # sugestia z auto-rules (do podglądu)


class AdminCampaignsResponse(BaseModel):
    campaigns: list[AdminCampaignRow]
    untagged_count: int


class AdminSetTypeRequest(BaseModel):
    type: str  # "acquisition" | "retarget" — walidacja w handlerze


class AdminSetTypeResponse(BaseModel):
    campaign_id: str
    campaign_type: str
    is_manual: bool
