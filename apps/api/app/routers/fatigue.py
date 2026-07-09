"""GET /api/fatigue — deterministyczne werdykty wypalenia kreacji (scripts/fatigue.py w pipeline).

Czyta z `snapshots/fatigue-{date}.json`. Jeśli dzisiejszy plik nie istnieje,
zwraca najnowszy dostępny + flag stale=True. Wzorzec 1:1 jak /api/insights.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from fastapi import APIRouter, Query

from ..deps import get_settings
from ..schemas import FatigueResponse

router = APIRouter()
log = logging.getLogger("fatigue")

_EMPTY = dict(ads=[], summary=None, window_days=None, generated_at=None, stale=True, date=None)


@router.get("/fatigue", response_model=FatigueResponse)
def get_fatigue(target_date: str | None = Query(None, alias="date")):
    """Zwraca fatigue werdykty dla danej daty (default: dziś). Fallback: najnowszy dostępny."""
    s = get_settings()
    snapshots_dir = s.snapshots_path
    if not snapshots_dir:
        return FatigueResponse(**_EMPTY)

    requested = target_date or date.today().isoformat()
    requested_path = snapshots_dir / f"fatigue-{requested}.json"

    stale = False
    if not requested_path.exists():
        # Fallback: najnowszy plik fatigue-*.json
        candidates = sorted(snapshots_dir.glob("fatigue-*.json"), reverse=True)
        if not candidates:
            log.warning("No fatigue files in %s", snapshots_dir)
            return FatigueResponse(**_EMPTY)
        requested_path = candidates[0]
        stale = True

    try:
        data = json.loads(requested_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to read %s: %s", requested_path, e)
        return FatigueResponse(**_EMPTY)

    return FatigueResponse(
        ads=data.get("ads", []),
        summary=data.get("summary"),
        window_days=data.get("window_days"),
        generated_at=data.get("generated_at"),
        stale=stale,
        date=data.get("date"),
    )
