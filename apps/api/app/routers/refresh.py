"""POST /api/refresh — invaliduje cache."""
from fastapi import APIRouter

from ..cache import cache
from ..schemas import RefreshResponse

router = APIRouter()


@router.post("/refresh", response_model=RefreshResponse)
def refresh():
    n = cache().invalidate()
    return RefreshResponse(invalidated_keys=n, snapshot_triggered=False)
