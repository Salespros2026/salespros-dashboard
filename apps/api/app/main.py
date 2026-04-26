"""FastAPI app entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .deps import get_settings
from .routers import overview, campaigns, adsets, creatives, funnel, refresh

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    log.info(
        "API start. Meta acct=%s, GHL loc=%s, snapshots_dir=%s, REQUIRE_CF_ACCESS=%s",
        s.META_AD_ACCOUNT_ID, s.GHL_LOCATION_ID, s.SNAPSHOTS_DIR, s.REQUIRE_CF_ACCESS,
    )
    yield


app = FastAPI(title="Salespros Dashboard API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cf_access_middleware(request: Request, call_next):
    """W produkcji wymagaj nagłówka Cf-Access-Authenticated-User-Email od Cloudflare Access.
    Lokalnie REQUIRE_CF_ACCESS=false — pomija."""
    if settings.REQUIRE_CF_ACCESS and request.url.path.startswith("/api/"):
        email = request.headers.get("Cf-Access-Authenticated-User-Email")
        if not email:
            raise HTTPException(status_code=401, detail="Missing Cloudflare Access identity")
    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": app.version}


@app.get("/")
def root():
    return {
        "service": "salespros-dashboard-api",
        "version": app.version,
        "docs": "/docs",
        "endpoints": [
            "/api/overview", "/api/campaigns", "/api/adsets",
            "/api/creatives", "/api/creatives/{ad_id}",
            "/api/funnel", "/api/refresh",
        ],
    }


app.include_router(overview.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(adsets.router, prefix="/api")
app.include_router(creatives.router, prefix="/api")
app.include_router(funnel.router, prefix="/api")
app.include_router(refresh.router, prefix="/api")
