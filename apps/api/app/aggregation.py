"""Wrapper nad attribution.aggregate_attribution — obsługuje range, brand split,
   wybór źródła (live/snapshot) i cache.
"""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# Reuse attribution.py który leży w `apps/api/attribution.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import attribution  # type: ignore  # noqa: E402

from .cache import cache
from .deps import get_settings
from .schemas import Brand

log = logging.getLogger("aggregation")


# ---------- Brand parsing ----------

def parse_brand(name: str) -> str:
    if not name:
        return Brand.OTHER
    n = name.lower()
    if "gawronify" in n:
        return Brand.GAWRONIFY
    if "salespros" in n or "sales pros" in n or "salespro" in n:
        return Brand.SALESPROS
    return Brand.OTHER


# ---------- Action type sums (mirror meta_daily_report.py) ----------

LEAD_ACTION_TYPES = {
    "offsite_conversion.fb_pixel_custom",
    "lead",
    "offsite_conversion.fb_pixel_lead",
    "submit_application",
    "complete_registration",
    "offsite_conversion.fb_pixel_complete_registration",
}


def sum_lead_actions(actions: list[dict] | None) -> int:
    if not actions:
        return 0
    seen: set[str] = set()
    total = 0
    for a in actions:
        at = a.get("action_type")
        if at in LEAD_ACTION_TYPES and at not in seen:
            try:
                total += int(float(a.get("value", 0)))
                seen.add(at)
            except (TypeError, ValueError):
                pass
    return total


# ---------- Live vs snapshot ----------

def get_meta_data(from_date: str, to_date: str, prefer_live: bool = True, full: bool = False) -> dict:
    """Zwraca strukturę zgodną z snapshotem Meta. Próbuje live, fallback snapshot.
    full=True: pobiera też adsets/ads/creatives (potrzebne dla /adsets i /creatives)."""
    if prefer_live:
        try:
            from .meta_client import build_meta_snapshot_like
            return build_meta_snapshot_like(since=from_date, until=to_date, full=full)
        except Exception as e:
            log.warning("Live Meta fetch failed (%s) — fallback snapshot", e)
    from .snapshot_loader import load_meta_snapshot
    return load_meta_snapshot(target_date=to_date) or {}


def get_meta_data_daily(level: str, from_date: str, to_date: str) -> list[dict]:
    """Insights per-day dla trend chartu (level: 'account' | 'campaign' | 'ad')."""
    try:
        from .meta_client import fetch_insights_daily
        return fetch_insights_daily(level, from_date, to_date)
    except Exception as e:
        log.warning("Daily insights fetch failed: %s", e)
        return []


def get_ghl_data(prefer_live: bool = True) -> dict:
    if prefer_live:
        try:
            from .ghl_client import build_ghl_snapshot_like
            return build_ghl_snapshot_like(days_back=60)
        except Exception as e:
            log.warning("Live GHL fetch failed (%s) — fallback snapshot", e)
    from .snapshot_loader import load_ghl_snapshot
    return load_ghl_snapshot() or {}


# ---------- Multi-day aggregation ----------

def daterange(from_date: str, to_date: str) -> list[str]:
    d = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    out = []
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def aggregate_range(meta: dict, ghl: dict, from_date: str, to_date: str) -> dict:
    """Sumuje per-day attribution dla zakresu dat. Zwraca:
    - totals: {real_leads, paid_contacts, ghosts, bookings, sales}
    - per_ad / per_campaign: zsumowane (leads, bookings, sales) — spend bierzemy raz z agregowanego insights
    - per_day: lista dziennych snapshotów do trend chartu
    """
    days = daterange(from_date, to_date)
    per_day = []
    totals = {
        "all_contacts": 0, "real_leads": 0, "ig_sync_ghosts": 0,
        "paid_contacts": 0, "organic_contacts": 0, "other_contacts": 0,
        "bookings": 0, "sales": 0,
        # Fix #A5: 3-bucket attribution
        "utm_attributed_leads": 0, "paid_unmapped_leads": 0, "untrackable_leads": 0,
        # Fix #A3: flow metric (calendar events ze startTime w okresie, niezależnie od daty leada)
        "bookings_in_period": 0,
    }
    per_ad: dict[str, dict] = {}
    per_campaign: dict[str, dict] = {}

    for d in days:
        try:
            r = attribution.aggregate_attribution(meta, ghl, d)
        except Exception as e:
            log.warning("aggregate_attribution failed for %s: %s", d, e)
            continue
        per_day.append({
            "date": d,
            "real_leads": r["real_leads_today"],
            "paid_contacts": r["paid_contacts"],
            "bookings": len(r["bookings_today"]),
        })
        totals["all_contacts"] += r["all_contacts_today"]
        totals["real_leads"] += r["real_leads_today"]
        totals["ig_sync_ghosts"] += r["ig_sync_ghosts"]
        totals["paid_contacts"] += r["paid_contacts"]
        totals["organic_contacts"] += r["organic_contacts"]
        totals["other_contacts"] += r["other_contacts"]
        totals["bookings"] += len(r["bookings_today"])
        # Fix #A5: 3-bucket
        totals["utm_attributed_leads"] += r.get("utm_attributed_leads", 0)
        totals["paid_unmapped_leads"] += r.get("paid_unmapped_leads", 0)
        totals["untrackable_leads"] += r.get("untrackable_leads", 0)
        for ad in r["per_ad"]:
            aid = ad["ad_id"]
            row = per_ad.setdefault(aid, {**ad, "leads": 0, "bookings": 0, "sales": 0, "revenue_pln": 0.0, "contacts": []})
            row["leads"] += ad["leads"]
            row["bookings"] += ad["bookings"]
            row["sales"] += ad["sales"]
            row["revenue_pln"] += ad.get("revenue_pln", 0.0)
            row["contacts"].extend(ad.get("contacts", []))
            totals["sales"] += ad.get("sales", 0)
        for c in r["per_campaign"]:
            cid = c["campaign_id"]
            row = per_campaign.setdefault(cid, {**c, "leads": 0, "bookings": 0, "sales": 0, "revenue_pln": 0.0})
            row["leads"] += c["leads"]
            row["bookings"] += c["bookings"]
            row["sales"] += c["sales"]
            row["revenue_pln"] += c.get("revenue_pln", 0.0)

    # Fix #A3: bookings_in_period = wszystkie calendar events ze startTime w okresie
    # Niezależne od daty leada — flow metric vs kohort metric.
    from datetime import date as _date
    from_d = _date.fromisoformat(from_date)
    to_d = _date.fromisoformat(to_date)
    bookings_in_period = 0
    # Reuse z attribution.py jako source of truth (zawiera "cancelled")
    BOOKED_STATUSES = attribution.BOOKED_APPOINTMENT_STATUSES
    for e in (ghl.get("calendar_events") or []):
        status = (e.get("appointmentStatus") or "").strip()
        if status not in BOOKED_STATUSES:
            continue
        st = e.get("startTime") or ""
        try:
            st_date = attribution.parse_iso(st).astimezone(attribution.LOCAL_TZ).date()
        except Exception:
            continue
        if from_d <= st_date <= to_d:
            bookings_in_period += 1
    totals["bookings_in_period"] = bookings_in_period

    # Spend dla całego range — z meta insights account-level (już agregowane przez Meta)
    insights_acct = (meta.get("insights") or {}).get("account") or []
    total_spend = sum(float(r.get("spend", 0) or 0) for r in insights_acct)
    insights_camp = (meta.get("insights") or {}).get("campaign") or []
    insights_ad = (meta.get("insights") or {}).get("ad") or []
    insights_adset = (meta.get("insights") or {}).get("adset") or []

    # Spend per ad/campaign — z aggregated insights (NIE per-day suma, bo per-day może mieć duplikaty)
    spend_by_ad = {ins.get("ad_id"): float(ins.get("spend", 0) or 0) for ins in insights_ad}
    spend_by_camp = {ins.get("campaign_id"): float(ins.get("spend", 0) or 0) for ins in insights_camp}
    meta_leads_by_ad = {ins.get("ad_id"): sum_lead_actions(ins.get("actions")) for ins in insights_ad}
    meta_leads_by_camp = {ins.get("campaign_id"): sum_lead_actions(ins.get("actions")) for ins in insights_camp}

    for aid, row in per_ad.items():
        row["spend"] = spend_by_ad.get(aid, row.get("spend", 0.0))
        row["meta_leads"] = meta_leads_by_ad.get(aid, 0)
        row["real_cpl"] = (row["spend"] / row["leads"]) if row["leads"] else None
        row["meta_cpl"] = (row["spend"] / row["meta_leads"]) if row["meta_leads"] else None
        row["real_cpb"] = (row["spend"] / row["bookings"]) if row["bookings"] else None
        row["cpa"] = (row["spend"] / row["sales"]) if row["sales"] else None
        row["roas"] = (row["revenue_pln"] / row["spend"]) if row["spend"] else None

    # Klasyfikacja kampanii — campaign_type per kampania (acquisition / retarget / unknown)
    from . import classifier
    camp_meta_by_id = {c.get("id"): c for c in (meta.get("campaigns") or [])}
    type_by_camp: dict[str, str] = {}

    for cid, row in per_campaign.items():
        row["spend"] = spend_by_camp.get(cid, row.get("spend", 0.0))
        row["meta_leads"] = meta_leads_by_camp.get(cid, 0)
        row["real_cpl"] = (row["spend"] / row["leads"]) if row["leads"] else None
        row["meta_cpl"] = (row["spend"] / row["meta_leads"]) if row["meta_leads"] else None
        row["real_cpb"] = (row["spend"] / row["bookings"]) if row["bookings"] else None
        row["cpa"] = (row["spend"] / row["sales"]) if row["sales"] else None
        row["roas"] = (row["revenue_pln"] / row["spend"]) if row["spend"] else None
        camp_meta = camp_meta_by_id.get(cid) or {"id": cid, "name": row.get("campaign_name", "")}
        ctype = classifier.classify_campaign(camp_meta)
        row["campaign_type"] = ctype
        type_by_camp[cid] = ctype

    # Także dla kampanii z insights ale bez per_campaign row (spend bez leadów GHL)
    for cid in spend_by_camp:
        if cid not in type_by_camp:
            camp_meta = camp_meta_by_id.get(cid) or {"id": cid}
            type_by_camp[cid] = classifier.classify_campaign(camp_meta)

    # Dla per_ad — dziedzicz typ z parent campaign
    for row in per_ad.values():
        cid = row.get("campaign_id", "")
        row["campaign_type"] = type_by_camp.get(cid, "unknown")

    # Total Meta leads (aggregated)
    if insights_acct:
        actions_total = (insights_acct[0].get("actions") or [])
        total_meta_leads = sum_lead_actions(actions_total)
    else:
        total_meta_leads = sum(meta_leads_by_camp.values())

    return {
        "from": from_date,
        "to": to_date,
        "total_spend": total_spend,
        "total_meta_leads": total_meta_leads,
        "totals": totals,
        "per_ad": list(per_ad.values()),
        "per_campaign": list(per_campaign.values()),
        "per_day": per_day,
        "insights_campaign": insights_camp,
        "insights_ad": insights_ad,
        "insights_adset": insights_adset,
        "campaign_type_by_id": type_by_camp,
    }


# ---------- Cache key builder ----------

def cache_key(*parts: object) -> str:
    return "|".join(str(p) for p in parts)


def get_attribution(from_date: str, to_date: str, prefer_live: bool = True, full: bool = False) -> dict:
    key = cache_key("attr", from_date, to_date, "live" if prefer_live else "snap", "full" if full else "lite")
    hit = cache().get(key)
    if hit is not None:
        return hit
    # Parallel Meta + GHL fetch — niezależne API, ~50% speedup vs sequential.
    with ThreadPoolExecutor(max_workers=2) as ex:
        meta_fut = ex.submit(get_meta_data, from_date, to_date, prefer_live, full)
        ghl_fut = ex.submit(get_ghl_data, prefer_live)
        meta = meta_fut.result()
        ghl = ghl_fut.result()
    if not meta or not ghl:
        return {"error": "no data", "from": from_date, "to": to_date}
    agg = aggregate_range(meta, ghl, from_date, to_date)
    agg["_meta_raw"] = meta
    agg["_ghl_raw"] = ghl
    # Lite (overview/campaigns/funnel): 5 min — Meta nie zmienia się szybciej.
    # Full (adsets/creatives): 15 min — droższy fetch (creatives × ad_ids), wolniej się zmienia.
    # Historical range (to_date < dziś): 1h — dane immutable po zamknięciu okna atrybucji.
    today = date.today().isoformat()
    if to_date < today:
        ttl = 3600
    else:
        ttl = 900 if full else 300
    cache().set(key, agg, ttl=ttl)
    return agg
