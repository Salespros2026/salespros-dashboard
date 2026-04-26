"""GET /api/overview — top-level KPI + daily trend."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Query

from ..aggregation import get_attribution, parse_brand, sum_lead_actions
from ..schemas import OverviewResponse, TrendPoint

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview(
    from_: str = Query(..., alias="from", description="YYYY-MM-DD"),
    to: str = Query(..., description="YYYY-MM-DD"),
    tz: str = Query("Europe/Warsaw"),
    brand: str = Query("all"),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live)
    if agg.get("error"):
        return OverviewResponse(
            from_=from_, to=to, tz=tz,
            spend=0.0, real_leads=0, meta_leads=0,
            real_cpl=None, meta_cpl=None, real_cpb=None,
            bookings=0, sales=0, ig_sync_ghosts=0,
            daily_trend=[], last_updated_iso=datetime.utcnow().isoformat() + "Z",
            data_source="empty",
        )

    meta = agg["_meta_raw"]
    camp_by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    spend_by_camp = {
        ins.get("campaign_id"): float(ins.get("spend", 0) or 0)
        for ins in agg["insights_campaign"]
    }

    def camp_brand(cid: str, camp_name: str = "") -> str:
        meta_obj = camp_by_id.get(cid, {})
        return parse_brand(meta_obj.get("name") or camp_name or "")

    if brand == "all":
        # Brand-agnostic: use pre-computed totals
        spend = agg["total_spend"]
        real_leads = agg["totals"]["real_leads"]
        bookings = agg["totals"]["bookings"]
        sales = agg["totals"]["sales"]
        ig_sync_ghosts = agg["totals"]["ig_sync_ghosts"]
        meta_leads = agg["total_meta_leads"]
    else:
        # Filter to brand campaigns only
        brand_cids: set[str] = set()
        # From per_campaign (GHL-attributed rows)
        for row in agg["per_campaign"]:
            if camp_brand(row["campaign_id"], row.get("campaign_name", "")) == brand:
                brand_cids.add(row["campaign_id"])
        # Also include campaigns that had spend but no GHL leads
        for ins in agg["insights_campaign"]:
            cid = ins.get("campaign_id", "")
            if camp_brand(cid, ins.get("campaign_name", "")) == brand:
                brand_cids.add(cid)

        spend = sum(spend_by_camp.get(cid, 0.0) for cid in brand_cids)
        real_leads = sum(
            row["leads"] for row in agg["per_campaign"]
            if row["campaign_id"] in brand_cids
        )
        bookings = sum(
            row["bookings"] for row in agg["per_campaign"]
            if row["campaign_id"] in brand_cids
        )
        sales = sum(
            row["sales"] for row in agg["per_campaign"]
            if row["campaign_id"] in brand_cids
        )
        meta_leads = sum(
            row.get("meta_leads", 0) for row in agg["per_campaign"]
            if row["campaign_id"] in brand_cids
        )
        ig_sync_ghosts = agg["totals"]["ig_sync_ghosts"]  # account-level, nie filtrujemy

    # Build daily trend — brand-filtered spend per day (campaign-level) + GHL leads/bookings from per_day
    from ..aggregation import get_meta_data_daily
    if brand == "all":
        daily_insights = get_meta_data_daily("account", from_, to)
        spend_by_day = {row.get("date_start"): float(row.get("spend", 0) or 0) for row in daily_insights}
    else:
        # Campaign-level daily insights → sum only brand campaigns
        daily_camp_insights = get_meta_data_daily("campaign", from_, to)
        spend_by_day: dict[str, float] = {}
        for row in daily_camp_insights:
            cid = row.get("campaign_id", "")
            if camp_brand(cid, row.get("campaign_name", "")) != brand:
                continue
            d = row.get("date_start", "")
            spend_by_day[d] = spend_by_day.get(d, 0.0) + float(row.get("spend", 0) or 0)

    trend: list[TrendPoint] = []
    for d in agg["per_day"]:
        date_str = d["date"]
        s = spend_by_day.get(date_str, 0.0)
        leads = d["real_leads"]
        cpl = (s / leads) if leads else None
        trend.append(TrendPoint(
            date=date_str, spend=s, leads=leads, real_cpl=cpl, bookings=d["bookings"],
        ))

    return OverviewResponse(
        from_=from_, to=to, tz=tz,
        spend=spend,
        real_leads=real_leads,
        meta_leads=meta_leads,
        real_cpl=(spend / real_leads) if real_leads else None,
        meta_cpl=(spend / meta_leads) if meta_leads else None,
        real_cpb=(spend / bookings) if bookings else None,
        bookings=bookings,
        sales=sales,
        ig_sync_ghosts=ig_sync_ghosts,
        daily_trend=trend,
        last_updated_iso=datetime.utcnow().isoformat() + "Z",
        data_source="live" if prefer_live else "snapshot",
    )
