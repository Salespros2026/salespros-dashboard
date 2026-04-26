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

    model_config = {"populate_by_name": True}


class CampaignRow(BaseModel):
    campaign_id: str
    name: str
    brand: str
    status: str
    objective: str | None = None
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
