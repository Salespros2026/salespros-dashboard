"""GET /api/overview — top-level KPI + daily trend."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Query

from ..aggregation import get_attribution, parse_brand, sum_lead_actions
from ..schemas import CplSplit, OverviewResponse, TrendPoint

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

    # Top-level spend = sum z daily_trend → karta Wydatek zgodna z wykresem.
    # Inaczej rozjazd: insights_campaign (time_increment=all_days) ≠ daily insights (time_increment=1).
    spend = sum(t.spend for t in trend)

    # CPL split: acquisition vs retarget — bazuje na agg["campaign_type_by_id"].
    # Spend per campaign bierzemy z spend_by_camp (insights all_days).
    # Leady GHL z agg["per_campaign"]. Filter po brand jak wyżej.
    type_by_camp: dict[str, str] = agg.get("campaign_type_by_id") or {}
    if brand == "all":
        cids_in_scope = set(spend_by_camp.keys()) | {row["campaign_id"] for row in agg["per_campaign"]}
    else:
        cids_in_scope = brand_cids  # type: ignore[name-defined]

    spend_by_type = {"acquisition": 0.0, "retarget": 0.0, "unknown": 0.0}
    leads_by_type = {"acquisition": 0, "retarget": 0, "unknown": 0}
    sales_by_type = {"acquisition": 0, "retarget": 0, "unknown": 0}
    revenue_by_type = {"acquisition": 0.0, "retarget": 0.0, "unknown": 0.0}
    bookings_by_type = {"acquisition": 0, "retarget": 0, "unknown": 0}
    untagged_count = 0
    for cid in cids_in_scope:
        ctype = type_by_camp.get(cid, "unknown")
        spend_by_type[ctype] = spend_by_type.get(ctype, 0.0) + spend_by_camp.get(cid, 0.0)
        if ctype == "unknown" and spend_by_camp.get(cid, 0.0) > 0:
            untagged_count += 1
    for row in agg["per_campaign"]:
        cid = row["campaign_id"]
        if cid not in cids_in_scope:
            continue
        ctype = type_by_camp.get(cid, "unknown")
        leads_by_type[ctype] = leads_by_type.get(ctype, 0) + int(row.get("leads", 0))
        sales_by_type[ctype] = sales_by_type.get(ctype, 0) + int(row.get("sales", 0))
        revenue_by_type[ctype] = revenue_by_type.get(ctype, 0.0) + float(row.get("revenue_pln", 0.0) or 0)
        bookings_by_type[ctype] = bookings_by_type.get(ctype, 0) + int(row.get("bookings", 0))

    # Re-engagement detection: leady przypisane do RTG creative ALE które miały
    # poprzedni touchpoint (czyli ad tylko re-aktywował). Liczymy z _ghl_raw contacts.
    import sys as _sys2
    _sys2.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
    import attribution as _attr  # type: ignore
    re_engaged_count = 0
    rtg_cids = {cid for cid in cids_in_scope if type_by_camp.get(cid) == "retarget"}
    for c in (agg["_ghl_raw"].get("contacts") or []):
        if not (c.get("email") or c.get("phone")):
            continue
        camp_id = _attr.get_meta_campaign_id(c)
        if camp_id not in rtg_cids:
            continue
        if _attr.is_re_engagement(c):
            re_engaged_count += 1

    split = CplSplit(
        spend_acquisition=spend_by_type["acquisition"],
        spend_retarget=spend_by_type["retarget"],
        spend_unknown=spend_by_type["unknown"],
        leads_acquisition=leads_by_type["acquisition"],
        leads_retarget=leads_by_type["retarget"],
        leads_unknown=leads_by_type["unknown"],
        cpl_acquisition=(spend_by_type["acquisition"] / leads_by_type["acquisition"]) if leads_by_type["acquisition"] else None,
        cpl_retarget=(spend_by_type["retarget"] / leads_by_type["retarget"]) if leads_by_type["retarget"] else None,
        untagged_count=untagged_count,
        sales_acquisition=sales_by_type["acquisition"],
        sales_retarget=sales_by_type["retarget"],
        revenue_acquisition=revenue_by_type["acquisition"],
        revenue_retarget=revenue_by_type["retarget"],
        cpa_acquisition=(spend_by_type["acquisition"] / sales_by_type["acquisition"]) if sales_by_type["acquisition"] else None,
        cpa_retarget=(spend_by_type["retarget"] / sales_by_type["retarget"]) if sales_by_type["retarget"] else None,
        roas_acquisition=(revenue_by_type["acquisition"] / spend_by_type["acquisition"]) if spend_by_type["acquisition"] else None,
        roas_retarget=(revenue_by_type["retarget"] / spend_by_type["retarget"]) if spend_by_type["retarget"] else None,
        bookings_acquisition=bookings_by_type["acquisition"],
        bookings_retarget=bookings_by_type["retarget"],
        re_engaged_leads_retarget=re_engaged_count,
        cost_per_booking_retarget=(spend_by_type["retarget"] / bookings_by_type["retarget"]) if bookings_by_type["retarget"] else None,
    )

    # Top-level revenue + CPA + ROAS — używamy FLOW metric (sales_in_period + revenue_in_period)
    # zamiast kohort (revenue_total z paid_contacts only). Kohort liczy tylko leady z UTM,
    # ale realne sales przychodzą też z organic / direct / starych contactów.
    revenue_flow = agg["totals"].get("revenue_in_period", 0.0)
    sales_flow = agg["totals"].get("sales_in_period", 0)

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
        split=split,
        revenue=revenue_flow,
        cpa=(spend / sales_flow) if sales_flow else None,
        roas=(revenue_flow / spend) if spend else None,
        # Fix #A5: 3-bucket attribution (account-level, brand-agnostic)
        utm_attributed_leads=agg["totals"].get("utm_attributed_leads", 0),
        paid_unmapped_leads=agg["totals"].get("paid_unmapped_leads", 0),
        untrackable_leads=agg["totals"].get("untrackable_leads", 0),
        # Fix #A3: flow metrics — bookings/sales/revenue ze wszystkich pipelines
        bookings_in_period=agg["totals"].get("bookings_in_period", 0),
        sales_in_period=agg["totals"].get("sales_in_period", 0),
        revenue_in_period=agg["totals"].get("revenue_in_period", 0.0),
    )
