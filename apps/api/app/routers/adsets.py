"""GET /api/adsets — per-adset rollup."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..aggregation import get_attribution, parse_brand, sum_lead_actions
from ..schemas import AdsetRow, AdsetsResponse

router = APIRouter()


@router.get("/adsets", response_model=AdsetsResponse)
def adsets(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    tz: str = Query("Europe/Warsaw"),
    brand: str = Query("all"),
    campaign_id: str | None = Query(None),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live, full=True)
    if agg.get("error"):
        return AdsetsResponse(adsets=[])

    meta = agg["_meta_raw"]
    adsets_by_id = {a["id"]: a for a in meta.get("adsets", [])}
    campaigns_by_id = {c["id"]: c for c in meta.get("campaigns", [])}
    insights_adset = {ins.get("adset_id"): ins for ins in agg["insights_adset"]}

    # Agregacja sales/bookings/revenue per adset — sumuj z per_ad pod parent adset_id
    ad_to_adset = {ad["id"]: ad.get("adset_id") for ad in meta.get("ads", []) if ad.get("adset_id")}
    sales_by_adset: dict[str, int] = {}
    bookings_by_adset: dict[str, int] = {}
    revenue_by_adset: dict[str, float] = {}
    for ad_row in agg.get("per_ad", []):
        asid = ad_to_adset.get(ad_row.get("ad_id"))
        if not asid:
            continue
        sales_by_adset[asid] = sales_by_adset.get(asid, 0) + int(ad_row.get("sales", 0))
        bookings_by_adset[asid] = bookings_by_adset.get(asid, 0) + int(ad_row.get("bookings", 0))
        revenue_by_adset[asid] = revenue_by_adset.get(asid, 0.0) + float(ad_row.get("revenue_pln", 0.0) or 0)

    # Agregacja GHL leads per adset_id (z attribution.utmTerm)
    leads_by_adset: dict[str, int] = {}
    contacts = (agg["_ghl_raw"].get("contacts") or [])
    from datetime import date
    from_d = date.fromisoformat(from_)
    to_d = date.fromisoformat(to)
    from attribution import get_meta_adset_id  # noqa: E402
    for c in contacts:
        if not c.get("email") and not c.get("phone"):
            continue
        adset_id = get_meta_adset_id(c)
        if not adset_id:
            continue
        # filter po dacie
        from datetime import datetime
        try:
            dt = datetime.fromisoformat((c.get("dateAdded") or "").replace("Z", "+00:00")).date()
        except Exception:
            continue
        if not (from_d <= dt <= to_d):
            continue
        leads_by_adset[str(adset_id)] = leads_by_adset.get(str(adset_id), 0) + 1

    rows: list[AdsetRow] = []
    for asid, ins in insights_adset.items():
        meta_obj = adsets_by_id.get(asid, {})
        parent_camp_id = meta_obj.get("campaign_id") or ins.get("campaign_id") or ""
        parent_camp = campaigns_by_id.get(parent_camp_id, {})
        if campaign_id and parent_camp_id != campaign_id:
            continue
        b = parse_brand(parent_camp.get("name") or "")
        if brand != "all" and b != brand:
            continue
        spend = float(ins.get("spend", 0) or 0)
        ghl_leads = leads_by_adset.get(asid, 0)
        sales = sales_by_adset.get(asid, 0)
        revenue = revenue_by_adset.get(asid, 0.0)
        rows.append(AdsetRow(
            adset_id=asid,
            name=meta_obj.get("name") or ins.get("adset_name") or asid,
            parent_campaign_id=parent_camp_id,
            parent_campaign_name=parent_camp.get("name") or ins.get("campaign_name") or "",
            brand=b,
            status=(meta_obj.get("effective_status") or meta_obj.get("status") or "?").upper(),
            optimization_goal=meta_obj.get("optimization_goal"),
            spend=spend,
            impressions=int(float(ins.get("impressions", 0) or 0)),
            ctr=float(ins.get("ctr", 0) or 0),
            frequency=float(ins.get("frequency", 0) or 0),
            meta_leads=sum_lead_actions(ins.get("actions")),
            ghl_leads=ghl_leads,
            real_cpl=(spend / ghl_leads) if ghl_leads else None,
            bookings=bookings_by_adset.get(asid, 0),
            sales=sales,
            revenue=revenue,
            cpa=(spend / sales) if sales else None,
            roas=(revenue / spend) if spend else None,
        ))
    rows.sort(key=lambda r: r.spend, reverse=True)
    return AdsetsResponse(adsets=rows)
