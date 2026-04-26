"""GoHighLevel REST client (live).

Token: Private Integration Token (PIT). Header `Authorization: Bearer <token>`,
`Version: 2021-07-28`. Endpoints: contacts search, opportunities search, pipelines,
custom fields, calendar events.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .deps import get_settings

log = logging.getLogger("ghl_client")

BASE = "https://services.leadconnectorhq.com"


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "Authorization": f"Bearer {s.GHL_PRIVATE_TOKEN}",
        "Version": s.GHL_API_VERSION,
        "Accept": "application/json",
    }


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE, headers=_headers(), timeout=httpx.Timeout(30.0))


def _paged(client: httpx.Client, path: str, params: dict, list_key: str, max_pages: int = 50) -> list[dict]:
    out: list[dict] = []
    page = 1
    while page <= max_pages:
        p = {**params, "page": page}
        r = client.get(path, params=p)
        if r.status_code == 429:
            log.warning("GHL 429 — backoff 2s")
            time.sleep(2)
            continue
        r.raise_for_status()
        body = r.json()
        items = body.get(list_key, [])
        out.extend(items)
        if len(items) < params.get("limit", 100):
            break
        page += 1
    return out


def search_contacts(days_back: int = 14, limit: int = 100) -> list[dict]:
    """Zwraca kontakty z ostatnich N dni. Używa /contacts/search z body POST,
    dla prostoty MVP używamy GET /contacts/ paged."""
    s = get_settings()
    with _client() as c:
        return _paged(
            c, "/contacts/",
            {"locationId": s.GHL_LOCATION_ID, "limit": limit},
            "contacts",
            max_pages=20,
        )


def get_pipelines() -> list[dict]:
    s = get_settings()
    with _client() as c:
        r = c.get("/opportunities/pipelines", params={"locationId": s.GHL_LOCATION_ID})
        r.raise_for_status()
        return r.json().get("pipelines", [])


def search_opportunities(limit: int = 100) -> list[dict]:
    s = get_settings()
    with _client() as c:
        return _paged(
            c, "/opportunities/search",
            {"location_id": s.GHL_LOCATION_ID, "limit": limit, "status": "all"},
            "opportunities",
            max_pages=20,
        )


def get_calendars() -> list[dict]:
    s = get_settings()
    with _client() as c:
        r = c.get("/calendars/", params={"locationId": s.GHL_LOCATION_ID})
        r.raise_for_status()
        return r.json().get("calendars", [])


def get_calendar_events(calendar_id: str, start_time_ms: int, end_time_ms: int) -> list[dict]:
    s = get_settings()
    with _client() as c:
        r = c.get(
            "/calendars/events",
            params={
                "locationId": s.GHL_LOCATION_ID,
                "calendarId": calendar_id,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
            },
        )
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("events", [])


def get_custom_fields() -> list[dict]:
    s = get_settings()
    with _client() as c:
        r = c.get(f"/locations/{s.GHL_LOCATION_ID}/customFields")
        r.raise_for_status()
        return r.json().get("customFields", [])


def build_ghl_snapshot_like(days_back: int = 14) -> dict:
    """Struktura zgodna z `snapshots/ghl-YYYY-MM-DD.json`."""
    s = get_settings()
    contacts = search_contacts(days_back=days_back)
    pipelines = get_pipelines()
    opportunities = search_opportunities()
    calendars = get_calendars()
    custom_fields = get_custom_fields()
    # Calendar events — ostatnie days_back dni
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days_back * 86400 * 1000
    events: list[dict] = []
    for cal in calendars:
        cid = cal.get("id")
        if not cid:
            continue
        try:
            events.extend(get_calendar_events(cid, start_ms, now_ms))
        except Exception as e:
            log.warning("Calendar events fetch failed for %s: %s", cid, e)
    return {
        "location_id": s.GHL_LOCATION_ID,
        "days_back": days_back,
        "pipelines": pipelines,
        "custom_field_defs": custom_fields,
        "contacts": contacts,
        "opportunities": opportunities,
        "calendars": calendars,
        "calendar_events": events,
    }
