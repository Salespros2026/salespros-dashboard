"""GET /api/historical-context — Meta historia 12 miesięcy + porównanie do bieżącego okresu.

Pobiera Meta insights za 4 okresy:
- current_7d: ostatnie 7 dni
- prev_30d: średnia z 30 dni przed obecnym (8-37 dni temu)
- prev_90d: średnia z 90 dni przed obecnym (8-97 dni temu)
- year_ago_30d: 30 dni z tego samego okresu rok temu

Plus liczy CPL = spend / leads (real_leads z GHL contacts).

Cache: result zapisywany do snapshots/historical_meta.json z TTL 24h.
Daily refresh przez `daily_run.sh`.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..aggregation import get_meta_data, get_ghl_data
from ..deps import get_settings
from ..schemas import HistoricalContextResponse, HistoricalPeriod

router = APIRouter()
log = logging.getLogger("historical")

CACHE_FILE = "historical_meta.json"
CACHE_TTL_HOURS = 24


def _count_real_leads_in_period(ghl_data: dict, from_iso: str, to_iso: str) -> int:
    """Policz real leads (email/phone) z GHL contacts w danym okresie."""
    from datetime import datetime
    contacts = ghl_data.get("contacts", []) or []
    from_d = date.fromisoformat(from_iso)
    to_d = date.fromisoformat(to_iso)
    count = 0
    for c in contacts:
        if not (c.get("email") or c.get("phone")):
            continue
        da = c.get("dateAdded", "")
        if not da:
            continue
        try:
            d = datetime.fromisoformat(da.replace("Z", "+00:00")).date()
        except Exception:
            continue
        if from_d <= d <= to_d:
            count += 1
    return count


def _fetch_meta_spend_for_period(from_iso: str, to_iso: str) -> float:
    """Pobiera Meta spend dla okresu (account-level, all_days)."""
    try:
        from ..meta_client import fetch_insights
        rows = fetch_insights("account", from_iso, to_iso)
        return sum(float(r.get("spend", 0) or 0) for r in rows)
    except Exception as e:
        log.warning("Meta fetch failed for %s..%s: %s", from_iso, to_iso, e)
        return 0.0


def _build_period(label: str, from_iso: str, to_iso: str, ghl_data: dict) -> HistoricalPeriod:
    spend = _fetch_meta_spend_for_period(from_iso, to_iso)
    leads = _count_real_leads_in_period(ghl_data, from_iso, to_iso)
    cpl = (spend / leads) if leads else None
    return HistoricalPeriod(
        label=label,
        from_=from_iso,
        to=to_iso,
        spend=spend,
        leads=leads,
        cpl=cpl,
    )


@router.get("/historical-context", response_model=HistoricalContextResponse)
def historical_context(force_refresh: bool = False):
    """Zwraca 4 okresy porównawcze: ostatnie 7d, prev 30d, prev 90d, rok temu 30d."""
    s = get_settings()
    snapshots_dir = s.snapshots_path
    cache_path = snapshots_dir / CACHE_FILE if snapshots_dir else None

    # Try cache
    if cache_path and cache_path.exists() and not force_refresh:
        from datetime import datetime
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            try:
                data = json.loads(cache_path.read_text())
                return HistoricalContextResponse(**data)
            except Exception as e:
                log.warning("Cache read failed: %s — recomputing", e)

    # Recompute
    log.info("Computing historical context (cache miss or force_refresh=True)")
    today = date.today()
    periods_def = [
        ("current_7d", today - timedelta(days=7), today),
        ("prev_30d", today - timedelta(days=37), today - timedelta(days=8)),
        ("prev_90d", today - timedelta(days=97), today - timedelta(days=8)),
        ("year_ago_30d", today - timedelta(days=395), today - timedelta(days=365)),
    ]

    # Pobieramy GHL contacts raz (60d snapshot pokrywa current+prev_30d+prev_90d,
    # ale nie year_ago — dla niego leads = 0, pokazujemy tylko spend Meta).
    ghl_data = get_ghl_data(prefer_live=True)

    periods = [_build_period(label, f.isoformat(), t.isoformat(), ghl_data) for label, f, t in periods_def]

    # Compute deltas (current vs prev_30d, vs year_ago)
    cur = next((p for p in periods if p.label == "current_7d"), None)
    prev30 = next((p for p in periods if p.label == "prev_30d"), None)
    yearago = next((p for p in periods if p.label == "year_ago_30d"), None)

    delta_vs_30d = None
    if cur and prev30 and cur.cpl and prev30.cpl:
        delta_vs_30d = round((cur.cpl / prev30.cpl - 1) * 100, 1)

    delta_vs_year = None
    if cur and yearago and cur.cpl and yearago.cpl:
        delta_vs_year = round((cur.cpl / yearago.cpl - 1) * 100, 1)

    from datetime import datetime
    response = HistoricalContextResponse(
        periods=periods,
        delta_cpl_vs_30d_pct=delta_vs_30d,
        delta_cpl_vs_year_pct=delta_vs_year,
        generated_at=datetime.utcnow().isoformat() + "Z",
    )

    # Save cache
    if cache_path:
        try:
            cache_path.write_text(response.model_dump_json(indent=2))
            log.info("Saved historical context cache to %s", cache_path)
        except Exception as e:
            log.warning("Cache save failed: %s", e)

    return response
