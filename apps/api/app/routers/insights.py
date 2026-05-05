"""GET /api/insights — najnowsze AI Insights (codziennie generowane przez scripts/ai_insights.py).

Czyta z `snapshots/insights-{date}.json`. Jeśli dzisiejszy plik nie istnieje,
zwraca najnowszy dostępny + flag stale=True.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Query

from ..deps import get_settings
from ..schemas import InsightsResponse

router = APIRouter()
log = logging.getLogger("insights")


@router.get("/insights", response_model=InsightsResponse)
def get_insights(target_date: str | None = Query(None, alias="date")):
    """Zwraca insights dla danej daty (default: dziś). Fallback: najnowszy dostępny."""
    s = get_settings()
    snapshots_dir = s.snapshots_path
    if not snapshots_dir:
        return InsightsResponse(insights=[], generated_at=None, stale=True, date=None, account_summary=None, model=None)

    requested = target_date or date.today().isoformat()
    requested_path = snapshots_dir / f"insights-{requested}.json"

    stale = False
    if not requested_path.exists():
        # Fallback: najnowszy plik insights-*.json
        candidates = sorted(snapshots_dir.glob("insights-*.json"), reverse=True)
        if not candidates:
            log.warning("No insights files in %s", snapshots_dir)
            return InsightsResponse(insights=[], generated_at=None, stale=True, date=None, account_summary=None, model=None)
        requested_path = candidates[0]
        stale = True

    try:
        data = json.loads(requested_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to read %s: %s", requested_path, e)
        return InsightsResponse(insights=[], generated_at=None, stale=True, date=None, account_summary=None, model=None)

    return InsightsResponse(
        insights=data.get("insights", []),
        generated_at=data.get("generated_at"),
        stale=stale,
        date=data.get("date"),
        account_summary=data.get("account_summary"),
        model=data.get("model"),
    )
