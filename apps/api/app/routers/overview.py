"""GET /api/overview — top-level KPI + daily trend."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Query

from ..aggregation import get_attribution, sum_lead_actions
from ..schemas import OverviewResponse, TrendPoint

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview(
    from_: str = Query(..., alias="from", description="YYYY-MM-DD"),
    to: str = Query(..., description="YYYY-MM-DD"),
    tz: str = Query("Europe/Warsaw"),
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

    spend = agg["total_spend"]
    real_leads = agg["totals"]["real_leads"]
    meta_leads = agg["total_meta_leads"]
    bookings = agg["totals"]["bookings"]

    # Build daily trend — łączymy spend per-day (z fetch_insights_daily) z leads/bookings z per_day attribution
    from ..aggregation import get_meta_data_daily
    daily_insights = get_meta_data_daily(from_, to)
    spend_by_day = {row.get("date_start"): float(row.get("spend", 0) or 0) for row in daily_insights}
    meta_leads_by_day = {row.get("date_start"): sum_lead_actions(row.get("actions")) for row in daily_insights}

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
        sales=agg["totals"]["sales"],
        ig_sync_ghosts=agg["totals"]["ig_sync_ghosts"],
        daily_trend=trend,
        last_updated_iso=datetime.utcnow().isoformat() + "Z",
        data_source="live" if prefer_live else "snapshot",
    )
