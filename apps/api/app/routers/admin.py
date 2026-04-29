"""GET/PATCH /api/admin/campaigns — manualne tagowanie kampanii ACQ/RTG.

Lista kampanii bierze meta z ostatnich 30 dni (po spend) — wystarczy do tego
co user widzi jako aktywne. Spend pomaga w sortowaniu i sygnalizuje co warto
otagować w pierwszej kolejności.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Path

from .. import classifier
from ..aggregation import get_attribution
from ..cache import cache
from ..schemas import (
    AdminCampaignRow,
    AdminCampaignsResponse,
    AdminSetTypeRequest,
    AdminSetTypeResponse,
)

router = APIRouter()


@router.get("/admin/campaigns", response_model=AdminCampaignsResponse)
def list_campaigns_for_admin():
    today = date.today()
    from_ = (today - timedelta(days=30)).isoformat()
    to = today.isoformat()
    agg = get_attribution(from_, to, prefer_live=True)
    if agg.get("error"):
        return AdminCampaignsResponse(campaigns=[], untagged_count=0)

    meta = agg["_meta_raw"]
    by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    spend_by_camp = {
        ins.get("campaign_id"): float(ins.get("spend", 0) or 0)
        for ins in agg.get("insights_campaign", [])
    }

    rows: list[AdminCampaignRow] = []
    untagged = 0
    seen: set[str] = set()
    for cid, camp in by_id.items():
        if cid in seen:
            continue
        seen.add(cid)
        camp_type = classifier.classify_campaign(camp)
        is_manual = classifier.is_manual(cid)
        suggested = classifier.suggest_for(camp)
        if camp_type == "unknown":
            untagged += 1
        rows.append(AdminCampaignRow(
            campaign_id=cid,
            name=camp.get("name", cid),
            objective=camp.get("objective"),
            status=(camp.get("effective_status") or camp.get("status") or "?").upper(),
            spend_30d=spend_by_camp.get(cid, 0.0),
            campaign_type=camp_type,
            is_manual=is_manual,
            suggested_type=suggested,
        ))

    rows.sort(key=lambda r: r.spend_30d, reverse=True)
    return AdminCampaignsResponse(campaigns=rows, untagged_count=untagged)


@router.patch("/admin/campaigns/{campaign_id}", response_model=AdminSetTypeResponse)
def set_campaign_type(
    body: AdminSetTypeRequest,
    campaign_id: str = Path(...),
):
    if body.type not in classifier.VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of {sorted(classifier.VALID_TYPES)}")
    classifier.set_manual(campaign_id, body.type)
    # Inwaliduj cache attribution — żeby nowe metryki się policzyły
    cache().invalidate(prefix="attr|")
    return AdminSetTypeResponse(
        campaign_id=campaign_id,
        campaign_type=body.type,
        is_manual=True,
    )


@router.delete("/admin/campaigns/{campaign_id}", response_model=AdminSetTypeResponse)
def clear_campaign_type(campaign_id: str = Path(...)):
    classifier.clear_manual(campaign_id)
    cache().invalidate(prefix="attr|")
    # Odbuduj klasyfikację (teraz z auto-rules)
    today = date.today()
    from_ = (today - timedelta(days=30)).isoformat()
    to = today.isoformat()
    agg = get_attribution(from_, to, prefer_live=True)
    meta = agg.get("_meta_raw") or {}
    by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    camp = by_id.get(campaign_id, {"id": campaign_id})
    new_type = classifier.classify_campaign(camp)
    return AdminSetTypeResponse(
        campaign_id=campaign_id,
        campaign_type=new_type,
        is_manual=False,
    )
