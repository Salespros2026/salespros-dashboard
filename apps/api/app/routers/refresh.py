"""POST /api/refresh — invaliduje cache (attribution + creative metadata + circuit breaker)."""
import logging

from fastapi import APIRouter

from ..cache import cache
from ..meta_client import clear_creative_cache, reset_circuit_breaker
from ..schemas import RefreshResponse

router = APIRouter()
log = logging.getLogger("refresh")


@router.post("/refresh", response_model=RefreshResponse)
def refresh():
    n = cache().invalidate()
    n_creatives = clear_creative_cache()
    breaker_was_armed = reset_circuit_breaker()
    log.info(
        "Refresh: invalidated %d attribution keys, cleared %d creative entries, breaker_was_armed=%s",
        n, n_creatives, breaker_was_armed,
    )
    return RefreshResponse(invalidated_keys=n, snapshot_triggered=False)
