"""GET /api/funnel — pipeline funnel z GHL (SalesPROs closing)."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query

from ..aggregation import get_attribution
from ..schemas import FunnelDropoff, FunnelResponse, FunnelStage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import attribution  # type: ignore  # noqa: E402

router = APIRouter()
log = logging.getLogger("funnel")

CLOSING_PIPELINE = "SalesPROs closing"
ORDERED_STAGES = [
    "Lead niekwalifikowany (setting)",
    "Nowy Lead",
    "Nowy lead po kontakcie",
    "Umówiona rozmowa",
    "Rozmowa nie odbyta",
    "Followup po rozmowie",
    "Nowy klient",
    "Opłacony START",
]


@router.get("/funnel", response_model=FunnelResponse)
def funnel(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    pipeline: str = Query(CLOSING_PIPELINE),
    prefer_live: bool = Query(True),
):
    agg = get_attribution(from_, to, prefer_live=prefer_live)
    if agg.get("error"):
        return FunnelResponse(pipeline_name=pipeline, stages=[], dropoff=[])

    pipelines = agg["_ghl_raw"].get("pipelines") or []
    target = next((p for p in pipelines if p.get("name") == pipeline), None)
    if not target:
        return FunnelResponse(pipeline_name=pipeline, stages=[], dropoff=[])

    opportunities = agg["_ghl_raw"].get("opportunities") or []
    stage_map = attribution.build_stage_map(pipelines)

    # Filter opportunities w pipeline + w zakresie dat (lastStageChangeAt)
    from datetime import date
    from_d = date.fromisoformat(from_)
    to_d = date.fromisoformat(to)

    by_stage_count: dict[str, int] = {}
    by_stage_value: dict[str, float] = {}
    for o in opportunities:
        sid = o.get("pipelineStageId") or o.get("pipelineStageUId")
        info = stage_map.get(sid, {})
        if info.get("pipeline_name") != pipeline:
            continue
        # Filtruj po dacie zmiany stage'a (lub createdAt jeśli brak)
        change = o.get("lastStageChangeAt") or o.get("createdAt")
        try:
            dt = datetime.fromisoformat((change or "").replace("Z", "+00:00")).date()
        except Exception:
            dt = None
        if dt and not (from_d <= dt <= to_d):
            continue
        stage_name = info.get("stage_name", "?")
        by_stage_count[stage_name] = by_stage_count.get(stage_name, 0) + 1
        try:
            by_stage_value[stage_name] = by_stage_value.get(stage_name, 0.0) + float(o.get("monetaryValue") or 0)
        except (TypeError, ValueError):
            pass

    stages = [
        FunnelStage(stage_name=s, count=by_stage_count.get(s, 0), value_pln=by_stage_value.get(s, 0.0))
        for s in ORDERED_STAGES
    ]

    dropoff: list[FunnelDropoff] = []
    for i in range(len(stages) - 1):
        prev, nxt = stages[i], stages[i + 1]
        if prev.count == 0:
            dropoff.append(FunnelDropoff(from_stage=prev.stage_name, to_stage=nxt.stage_name, rate=0.0))
        else:
            rate = 1 - (nxt.count / prev.count)
            dropoff.append(FunnelDropoff(from_stage=prev.stage_name, to_stage=nxt.stage_name, rate=max(0.0, rate)))

    return FunnelResponse(pipeline_name=pipeline, stages=stages, dropoff=dropoff)
