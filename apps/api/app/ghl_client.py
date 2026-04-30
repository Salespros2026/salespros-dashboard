"""GoHighLevel REST client (live).

Token: Private Integration Token (PIT). Header `Authorization: Bearer <token>`,
`Version: 2021-07-28`. Endpoints: contacts search, opportunities search, pipelines,
custom fields, calendar events.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
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


def search_contacts(days_back: int = 60, limit: int = 100) -> list[dict]:
    """Zwraca kontakty utworzone w ostatnich N dni. POST /contacts/search z searchAfter
    paginacja (GHL ignoruje `page` na GET /contacts/, więc ten wariant zawodzi
    przy >100 contactach)."""
    from datetime import datetime, timedelta, timezone
    s = get_settings()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    contacts: list[dict] = []
    search_after = None
    headers = {**_headers(), "Content-Type": "application/json"}
    with httpx.Client(base_url=BASE, headers=headers, timeout=httpx.Timeout(30.0)) as c:
        for page in range(1, 51):  # safety cap 50 pages × 100 = 5000
            body: dict = {
                "locationId": s.GHL_LOCATION_ID,
                "pageLimit": limit,
                "sort": [{"field": "dateAdded", "direction": "desc"}],
            }
            if search_after:
                body["searchAfter"] = search_after
            r = c.post("/contacts/search", json=body)
            if r.status_code == 429:
                log.warning("GHL 429 — backoff 2s")
                time.sleep(2)
                continue
            r.raise_for_status()
            data = r.json()
            batch = data.get("contacts", [])
            if not batch:
                break
            contacts.extend(batch)
            oldest = batch[-1].get("dateAdded", "")
            if oldest < cutoff:
                # Przytnij do cutoff i wyjdź
                contacts = [c for c in contacts if (c.get("dateAdded") or "") >= cutoff]
                break
            search_after = batch[-1].get("searchAfter")
            if not search_after:
                break
    return contacts


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


def build_ghl_snapshot_like(days_back: int = 60) -> dict:
    """Struktura zgodna z `snapshots/ghl-YYYY-MM-DD.json`.
    Parallel fetch 5 niezależnych endpointów + calendar events per calendar.
    days_back=60 daje pełny miesiąc + miesiąc baseline."""
    s = get_settings()

    # Faza 1 — 5 endpointów równolegle (contacts, pipelines, opps, calendars, custom fields).
    # Każdy ma swoją wewnętrzną paginację (sync), ale są niezależne od siebie.
    with ThreadPoolExecutor(max_workers=5) as ex:
        contacts_fut = ex.submit(search_contacts, days_back)
        pipelines_fut = ex.submit(get_pipelines)
        opps_fut = ex.submit(search_opportunities)
        calendars_fut = ex.submit(get_calendars)
        custom_fields_fut = ex.submit(get_custom_fields)
        contacts = contacts_fut.result()
        pipelines = pipelines_fut.result()
        opportunities = opps_fut.result()
        calendars = calendars_fut.result()
        custom_fields = custom_fields_fut.result()

    # Faza 2 — events per calendar równolegle (zwykle 8-12 kalendarzy).
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days_back * 86400 * 1000
    events: list[dict] = []
    cal_ids = [c.get("id") for c in calendars if c.get("id")]
    if cal_ids:
        with ThreadPoolExecutor(max_workers=min(10, len(cal_ids))) as ex:
            futures = {cid: ex.submit(get_calendar_events, cid, start_ms, now_ms) for cid in cal_ids}
            for cid, fut in futures.items():
                try:
                    events.extend(fut.result())
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
