"""GET /api/campaigns — per-campaign rollup."""
from __future__ import annotations

from fastapi import APIRouter, Query

from .. import classifier
from ..aggregation import get_attribution, parse_brand
from ..schemas import CampaignRow, CampaignsResponse

router = APIRouter()


@router.get("/campaigns", response_model=CampaignsResponse)
def campaigns(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    tz: str = Query("Europe/Warsaw"),
    brand: str = Query("all"),
    status: str = Query("all", description="all | active | paused"),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live)
    if agg.get("error"):
        return CampaignsResponse(campaigns=[])

    meta = agg["_meta_raw"]
    by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    insights_camp = {ins.get("campaign_id"): ins for ins in agg["insights_campaign"]}
    type_by_camp: dict[str, str] = agg.get("campaign_type_by_id") or {}

    rows: list[CampaignRow] = []
    seen_ids = set()

    for camp_agg in agg["per_campaign"]:
        cid = camp_agg["campaign_id"]
        seen_ids.add(cid)
        meta_obj = by_id.get(cid, {})
        ins = insights_camp.get(cid, {})
        b = parse_brand(meta_obj.get("name") or camp_agg.get("campaign_name") or "")

        if brand != "all" and b != brand:
            continue

        camp_status = (meta_obj.get("effective_status") or meta_obj.get("status") or "?").upper()
        if status == "active" and camp_status != "ACTIVE":
            continue
        if status == "paused" and camp_status not in ("PAUSED", "CAMPAIGN_PAUSED"):
            continue

        daily_budget = meta_obj.get("daily_budget")
        try:
            db = float(daily_budget) / 100 if daily_budget else None
        except (TypeError, ValueError):
            db = None

        rows.append(CampaignRow(
            campaign_id=cid,
            name=meta_obj.get("name") or camp_agg.get("campaign_name") or cid,
            brand=b,
            status=camp_status,
            objective=meta_obj.get("objective"),
            campaign_type=type_by_camp.get(cid, "unknown"),
            is_manual_type=classifier.is_manual(cid),
            spend=camp_agg.get("spend", 0.0),
            impressions=int(float(ins.get("impressions", 0) or 0)),
            ctr=float(ins.get("ctr", 0) or 0),
            cpm=float(ins.get("cpm", 0) or 0),
            frequency=float(ins.get("frequency", 0) or 0),
            meta_leads=camp_agg.get("meta_leads", 0),
            ghl_leads=camp_agg.get("leads", 0),
            real_cpl=camp_agg.get("real_cpl"),
            meta_cpl=camp_agg.get("meta_cpl"),
            bookings=camp_agg.get("bookings", 0),
            sales=camp_agg.get("sales", 0),
            revenue=camp_agg.get("revenue_pln", 0.0),
            cpa=camp_agg.get("cpa"),
            roas=camp_agg.get("roas"),
            daily_budget=db,
        ))

    # Dorzuć kampanie które miały spend ale nie miały leadów GHL (żeby nie znikały z UI)
    for cid, ins in insights_camp.items():
        if cid in seen_ids:
            continue
        meta_obj = by_id.get(cid, {})
        b = parse_brand(meta_obj.get("name") or ins.get("campaign_name") or "")
        if brand != "all" and b != brand:
            continue
        camp_status = (meta_obj.get("effective_status") or meta_obj.get("status") or "?").upper()
        if status == "active" and camp_status != "ACTIVE":
            continue
        if status == "paused" and camp_status not in ("PAUSED", "CAMPAIGN_PAUSED"):
            continue
        spend = float(ins.get("spend", 0) or 0)
        if spend == 0 and status == "all" and camp_status not in ("ACTIVE",):
            continue
        from ..aggregation import sum_lead_actions
        meta_leads = sum_lead_actions(ins.get("actions"))
        rows.append(CampaignRow(
            campaign_id=cid,
            name=meta_obj.get("name") or ins.get("campaign_name") or cid,
            brand=b,
            status=camp_status,
            objective=meta_obj.get("objective"),
            campaign_type=type_by_camp.get(cid, "unknown"),
            is_manual_type=classifier.is_manual(cid),
            spend=spend,
            impressions=int(float(ins.get("impressions", 0) or 0)),
            ctr=float(ins.get("ctr", 0) or 0),
            cpm=float(ins.get("cpm", 0) or 0),
            frequency=float(ins.get("frequency", 0) or 0),
            meta_leads=meta_leads,
            ghl_leads=0,
            real_cpl=None,
            meta_cpl=(spend / meta_leads) if meta_leads else None,
            bookings=0,
            sales=0,
        ))

    rows.sort(key=lambda r: r.spend, reverse=True)
    return CampaignsResponse(campaigns=rows)
