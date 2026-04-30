"""GET /api/creatives + GET /api/creatives/{ad_id} — per kreacja + drill-down."""
from __future__ import annotations

import logging
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Query

from ..aggregation import get_attribution, parse_brand, sum_lead_actions
from ..deps import get_settings
from ..schemas import (
    CreativeContact, CreativeDetailResponse, CreativeRow, CreativesResponse, TrendPoint,
)

router = APIRouter()
log = logging.getLogger("creatives")

GHL_CONTACT_URL = "https://app.gohighlevel.com/v2/location/{loc}/contacts/detail/{cid}"


@router.get("/creatives", response_model=CreativesResponse)
def creatives(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    tz: str = Query("Europe/Warsaw"),
    brand: str = Query("all"),
    campaign_id: str | None = Query(None),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live, full=True)
    if agg.get("error"):
        return CreativesResponse(creatives=[], avg_real_cpl=None)

    meta = agg["_meta_raw"]
    ads_by_id = {a["id"]: a for a in meta.get("ads", [])}
    creatives_by_ad_id = meta.get("creatives_by_ad_id") or {}
    campaigns_by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    insights_ad = {ins.get("ad_id"): ins for ins in agg["insights_ad"]}

    # Build map ad_id → ghl rollup z agg["per_ad"]
    per_ad_map = {a["ad_id"]: a for a in agg["per_ad"]}

    rows: list[CreativeRow] = []
    for ad_id, ins in insights_ad.items():
        ad_meta = ads_by_id.get(ad_id, {})
        creative = creatives_by_ad_id.get(ad_id, {})
        camp_id = ad_meta.get("campaign_id") or ins.get("campaign_id") or ""
        camp = campaigns_by_id.get(camp_id, {})
        b = parse_brand(camp.get("name") or ins.get("campaign_name") or "")
        if brand != "all" and b != brand:
            continue
        if campaign_id and camp_id != campaign_id:
            continue
        spend = float(ins.get("spend", 0) or 0)
        impressions = int(float(ins.get("impressions", 0) or 0))
        ghl_row = per_ad_map.get(ad_id, {})
        ghl_leads = ghl_row.get("leads", 0)
        meta_leads = sum_lead_actions(ins.get("actions"))

        # Hook rate = 3-sec views / impressions. Meta liczy 3-sec views poprzez
        # actions[].action_type='video_view' (NIE osobne pole — to przyczyna regresji).
        # Hold rate = video_p50 / video_p25 (50% retention z tych co dotrwali do 25%).
        def _sum_first(action_list):
            if not action_list:
                return 0
            try:
                return sum(int(float(a.get("value", 0))) for a in action_list)
            except (TypeError, ValueError):
                return 0

        def _action_value(actions, action_type):
            if not actions:
                return 0
            for a in actions:
                if a.get("action_type") == action_type:
                    try:
                        return int(float(a.get("value", 0)))
                    except (TypeError, ValueError):
                        return 0
            return 0

        v3s = _action_value(ins.get("actions"), "video_view")
        v25 = _sum_first(ins.get("video_p25_watched_actions"))
        v50 = _sum_first(ins.get("video_p50_watched_actions"))
        hook_rate = (v3s / impressions) if impressions and v3s else None
        hold_rate = (v50 / v25) if v25 and v50 else None

        # Creative Health Score (composite z creative-rules.md)
        from ..scoring import compute_health_score
        health_score, health_status = compute_health_score(
            spend=spend,
            real_cpl=ghl_row.get("real_cpl"),
            hook_rate=hook_rate,
            hold_rate=hold_rate,
            ctr=float(ins.get("ctr", 0) or 0),
            frequency=float(ins.get("frequency", 0) or 0),
        )

        rows.append(CreativeRow(
            ad_id=ad_id,
            ad_name=ad_meta.get("name") or ins.get("ad_name") or ad_id,
            campaign_name=camp.get("name") or ins.get("campaign_name") or "",
            brand=b,
            status=(ad_meta.get("effective_status") or ad_meta.get("status") or "?").upper(),
            thumbnail_url=creative.get("thumbnail_url") or creative.get("image_url"),
            video_id=creative.get("video_id"),
            creative_title=creative.get("title"),
            creative_body=(creative.get("body") or "")[:300] or None,
            spend=spend,
            impressions=impressions,
            ctr=float(ins.get("ctr", 0) or 0),
            cpm=float(ins.get("cpm", 0) or 0),
            frequency=float(ins.get("frequency", 0) or 0),
            meta_leads=meta_leads,
            ghl_leads=ghl_leads,
            real_cpl=ghl_row.get("real_cpl"),
            meta_cpl=(spend / meta_leads) if meta_leads else None,
            bookings=ghl_row.get("bookings", 0),
            sales=ghl_row.get("sales", 0),
            revenue=ghl_row.get("revenue_pln", 0.0),
            cpa=ghl_row.get("cpa"),
            roas=ghl_row.get("roas"),
            hook_rate=hook_rate,
            hold_rate=hold_rate,
            health_score=health_score,
            health_status=health_status,
        ))

    # Winner / loser badges — bazując na real_cpl wzgl. avg
    cpls = [r.real_cpl for r in rows if r.real_cpl is not None and r.spend >= 30]
    avg_cpl = (sum(cpls) / len(cpls)) if cpls else None
    if avg_cpl:
        for r in rows:
            if r.real_cpl is None or r.spend < 30:
                continue
            if r.real_cpl < 0.8 * avg_cpl:
                r.winner_badge = True
            elif r.real_cpl > 1.5 * avg_cpl and r.spend >= 50:
                r.loser_badge = True

    rows.sort(key=lambda r: r.spend, reverse=True)
    return CreativesResponse(creatives=rows, avg_real_cpl=avg_cpl)


@router.get("/creatives/{ad_id}", response_model=CreativeDetailResponse)
def creative_detail(
    ad_id: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live, full=True)
    if agg.get("error"):
        raise HTTPException(404, "No data")
    meta = agg["_meta_raw"]
    ads_by_id = {a["id"]: a for a in meta.get("ads", [])}
    creatives_by_ad_id = meta.get("creatives_by_ad_id") or {}
    campaigns_by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    ad = ads_by_id.get(ad_id)
    if not ad:
        raise HTTPException(404, f"Ad {ad_id} not found in account")
    camp = campaigns_by_id.get(ad.get("campaign_id"), {})
    creative = creatives_by_ad_id.get(ad_id, {})

    # Trend per-day dla tego ada
    try:
        from ..meta_client import fetch_insights_daily
        daily = fetch_insights_daily("ad", from_, to)
    except Exception as e:
        log.warning("Daily ad insights failed: %s", e)
        daily = []
    trend: list[TrendPoint] = []
    for row in daily:
        if row.get("ad_id") != ad_id:
            continue
        d = row.get("date_start")
        s = float(row.get("spend", 0) or 0)
        ml = sum_lead_actions(row.get("actions"))
        trend.append(TrendPoint(
            date=d, spend=s, leads=ml,
            real_cpl=(s / ml) if ml else None, bookings=0,
        ))

    # Lista contactów które przyszły z tego ad
    settings = get_settings()
    contacts: list[CreativeContact] = []
    from_d = date.fromisoformat(from_)
    to_d = date.fromisoformat(to)
    pipelines = agg["_ghl_raw"].get("pipelines") or []
    import sys as _sys
    _sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
    import attribution  # type: ignore
    stage_map = attribution.build_stage_map(pipelines)
    opportunities = agg["_ghl_raw"].get("opportunities") or []
    calendar_events = agg["_ghl_raw"].get("calendar_events") or []  # Fix #A3

    for c in agg["_ghl_raw"].get("contacts") or []:
        if not (c.get("email") or c.get("phone")):
            continue
        attr_src = c.get("attributionSource") or c.get("lastAttributionSource") or {}
        if str(attr_src.get("utmContent") or "") != ad_id:
            continue
        try:
            dt = datetime.fromisoformat((c.get("dateAdded") or "").replace("Z", "+00:00")).date()
        except Exception:
            continue
        if not (from_d <= dt <= to_d):
            continue
        cid = c["id"]
        contacts.append(CreativeContact(
            contact_id=cid,
            name=((c.get("firstName") or "") + " " + (c.get("lastName") or "")).strip()
                 or c.get("email") or "(brak imienia)",
            email=c.get("email"),
            phone=c.get("phone"),
            date_added=c.get("dateAdded") or "",
            booked=attribution.is_booked(cid, opportunities, stage_map, calendar_events),
            sold=attribution.is_sold(cid, opportunities, stage_map),
            ghl_url=GHL_CONTACT_URL.format(loc=settings.GHL_LOCATION_ID, cid=cid),
        ))

    return CreativeDetailResponse(
        ad_id=ad_id,
        ad_name=ad.get("name") or ad_id,
        campaign_name=camp.get("name") or "",
        brand=parse_brand(camp.get("name") or ""),
        creative=creative,
        trend=trend,
        leads=contacts,
    )
