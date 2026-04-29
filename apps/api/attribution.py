"""
Attribution module — łączy Meta Ads snapshot z GoHighLevel snapshot.

Każdy lead w GHL z `attributionSource.utmContent` zawiera Meta ad_id (jako string).
Mapowanie:
- utmSource ∈ {facebook, ig} → Paid Social z Meta Ads
- medium = 'instagram' → Organic Instagram (Reels, posts)
- medium = 'form' → Lead Form Meta
- campaign = Meta campaign ID
- utmContent = Meta ad ID
- utmTerm = Meta ad set ID

Stages w pipeline "SalesPROs closing":
- "Umówiona rozmowa" = booking
- "Nowy klient" / "Opłacony START" = sale
"""
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Strefa czasowa do interpretacji "dziś" — biznes Salespros jest w Polsce, ale user może być
# w podróży. Default = system local. Override przez env var REPORT_TIMEZONE.
_tz_name = os.environ.get("REPORT_TIMEZONE")
if _tz_name:
    LOCAL_TZ = ZoneInfo(_tz_name)
else:
    LOCAL_TZ = datetime.now().astimezone().tzinfo or ZoneInfo("Europe/Warsaw")

# Stages bookingu (z `SalesPROs closing` pipeline)
BOOKING_STAGES = {"Umówiona rozmowa"}
# Stages sprzedaży
SALE_STAGES = {"Nowy klient", "Opłacony START"}
# Stages negative outcomes
LOST_STAGES = {"Niegotowy", "Niekwalfikowany/ LOST", "Lead Duch", "Lead niekwalifikowany (setting)", "Rozmowa nie odbyta"}

# Pipeline ID głównego pipeline closing (z snapshotu)
CLOSING_PIPELINE_NAME = "SalesPROs closing"


def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def is_real_lead(contact: dict) -> bool:
    """
    Filtr 'realnego leada' — kontakt ma mail LUB telefon LUB tag wskazujący lead.
    Wycina IG-sync ghosts (followersi, polubienia, dotknięcia bota IG bez kwalifikacji),
    którzy są w GHL bez danych kontaktowych.
    """
    if contact.get("email") or contact.get("phone"):
        return True
    tags = contact.get("tags") or []
    if any("lead" in (t or "").lower() for t in tags):
        return True
    return False


def _attr_sources(contact: dict) -> list[dict]:
    """Zwraca wszystkie attribution objects danego kontaktu.
    GHL nowy format: lista pod kluczem `attributions`. Stary format (deprecated):
    `attributionSource` + `lastAttributionSource` jako dict.
    Sprawdzamy oba dla compatibility."""
    out: list[dict] = []
    arr = contact.get("attributions")
    if isinstance(arr, list):
        out.extend(a for a in arr if isinstance(a, dict))
    for key in ("attributionSource", "lastAttributionSource"):
        a = contact.get(key)
        if isinstance(a, dict) and a:
            out.append(a)
    return out


def is_paid_social(contact: dict) -> bool:
    """Czy kontakt przyszedł z Meta Ads (paid social)?"""
    for a in _attr_sources(contact):
        # nowy format: utmSessionSource. stary: sessionSource.
        if a.get("utmSessionSource") == "Paid Social" or a.get("sessionSource") == "Paid Social":
            return True
        src = (a.get("utmSource") or "").lower()
        med = (a.get("utmMedium") or "").lower()
        if src in ("facebook", "ig", "instagram") and med == "paid":
            return True
    return False


def is_organic_instagram(contact: dict) -> bool:
    """Kontakt z organic Instagram (Reels, posts, DM)?"""
    if is_paid_social(contact):
        return False
    for a in _attr_sources(contact):
        if a.get("medium") == "instagram":
            return True
        if a.get("sessionSource") == "Social media" and a.get("medium") == "instagram":
            return True
    return False


def get_meta_ad_id(contact: dict) -> str | None:
    """Wyciąga Meta ad ID (utmContent) z kontaktu."""
    for a in _attr_sources(contact):
        ad_id = a.get("utmContent")
        if ad_id:
            return str(ad_id)
    return None


def get_meta_campaign_id(contact: dict) -> str | None:
    """Wyciąga Meta campaign ID. Nowy format: utmCampaign. Stary: campaign."""
    for a in _attr_sources(contact):
        cid = a.get("utmCampaign") or a.get("campaign")
        if cid:
            return str(cid)
    return None


def get_meta_adset_id(contact: dict) -> str | None:
    for a in _attr_sources(contact):
        sid = a.get("utmTerm")
        if sid:
            return str(sid)
    return None


def filter_contacts_for_date(contacts: list[dict], target_date: str) -> list[dict]:
    """Zwraca kontakty utworzone w danym dniu w strefie Europe/Warsaw.
    target_date format: YYYY-MM-DD (lokalna data)."""
    out = []
    for c in contacts:
        da = c.get("dateAdded") or ""
        dt = parse_iso(da)
        if not dt:
            continue
        local = dt.astimezone(LOCAL_TZ)
        if local.date().isoformat() == target_date:
            out.append(c)
    return out


def build_stage_map(pipelines: list[dict]) -> dict[str, dict]:
    """Mapuje stage_id → {pipeline_name, stage_name}."""
    out = {}
    for p in pipelines:
        for s in p.get("stages", []):
            out[s.get("id")] = {
                "pipeline_id": p.get("id"),
                "pipeline_name": p.get("name"),
                "stage_name": s.get("name"),
            }
    return out


def get_closing_pipeline_id(pipelines: list[dict]) -> str | None:
    for p in pipelines:
        if p.get("name") == CLOSING_PIPELINE_NAME:
            return p.get("id")
    return None


def opportunities_for_contact(opportunities: list[dict], contact_id: str) -> list[dict]:
    return [o for o in opportunities if o.get("contactId") == contact_id]


def is_booked(contact_id: str, opportunities: list[dict], stage_map: dict) -> bool:
    for o in opportunities_for_contact(opportunities, contact_id):
        sid = o.get("pipelineStageId") or o.get("pipelineStageUId")
        info = stage_map.get(sid, {})
        if info.get("stage_name") in BOOKING_STAGES:
            return True
        # Bookingi też stages ZA "Umówiona rozmowa" — bo lead awansował
        if info.get("stage_name") in {"Followup po rozmowie", "Nowy klient", "Opłacony START"}:
            return True
    return False


def is_sold(contact_id: str, opportunities: list[dict], stage_map: dict) -> bool:
    for o in opportunities_for_contact(opportunities, contact_id):
        sid = o.get("pipelineStageId") or o.get("pipelineStageUId")
        info = stage_map.get(sid, {})
        if info.get("stage_name") in SALE_STAGES:
            return True
    return False


def revenue_for_contact(contact_id: str, opportunities: list[dict], stage_map: dict) -> float:
    """Suma monetaryValue z opportunities danego contacta które są w SALE_STAGES.
    Jeden contact może mieć kilka opp (np. upsell) — sumujemy wszystkie sold."""
    total = 0.0
    for o in opportunities_for_contact(opportunities, contact_id):
        sid = o.get("pipelineStageId") or o.get("pipelineStageUId")
        info = stage_map.get(sid, {})
        if info.get("stage_name") not in SALE_STAGES:
            continue
        try:
            total += float(o.get("monetaryValue") or 0)
        except (TypeError, ValueError):
            pass
    return total


def aggregate_attribution(meta_snapshot: dict, ghl_snapshot: dict, target_date: str) -> dict:
    """Główna funkcja — łączy Meta + GHL i zwraca agregat per-ad i per-campaign."""
    all_today = filter_contacts_for_date(ghl_snapshot["contacts"], target_date)
    # Realnych leadów (mail/tel/tag) — odfiltruj IG-sync ghosts (no email, no phone, no lead tag)
    contacts_today = [c for c in all_today if is_real_lead(c)]
    ghosts_today = [c for c in all_today if not is_real_lead(c)]

    paid_contacts = [c for c in contacts_today if is_paid_social(c)]
    organic_contacts = [c for c in contacts_today if is_organic_instagram(c)]
    other_contacts = [c for c in contacts_today if not is_paid_social(c) and not is_organic_instagram(c)]

    pipelines = ghl_snapshot.get("pipelines", [])
    stage_map = build_stage_map(pipelines)
    opportunities = ghl_snapshot.get("opportunities", [])

    # Mapowanie Meta ad_id → meta data (spend, name, etc.)
    meta_ad_map = {}
    for ad in meta_snapshot.get("ads", []):
        meta_ad_map[ad["id"]] = {"name": ad.get("name", "?"), "campaign_id": ad.get("campaign_id")}
    meta_ad_insights = {ins.get("ad_id"): ins for ins in meta_snapshot.get("insights", {}).get("ad", [])}
    meta_campaign_insights = {ins.get("campaign_id"): ins for ins in meta_snapshot.get("insights", {}).get("campaign", [])}
    meta_campaign_meta = {c["id"]: c for c in meta_snapshot.get("campaigns", [])}

    # Per-ad attribution z paid_contacts
    per_ad = {}
    for c in paid_contacts:
        ad_id = get_meta_ad_id(c)
        if not ad_id:
            ad_id = "(unmapped-paid)"
        if ad_id not in per_ad:
            per_ad[ad_id] = {
                "ad_id": ad_id,
                "leads": 0,
                "bookings": 0,
                "sales": 0,
                "revenue_pln": 0.0,
                "contacts": [],
            }
        per_ad[ad_id]["leads"] += 1
        cid = c.get("id")
        if is_booked(cid, opportunities, stage_map):
            per_ad[ad_id]["bookings"] += 1
        if is_sold(cid, opportunities, stage_map):
            per_ad[ad_id]["sales"] += 1
            per_ad[ad_id]["revenue_pln"] += revenue_for_contact(cid, opportunities, stage_map)
        per_ad[ad_id]["contacts"].append({
            "id": cid,
            "name": ((c.get("firstName") or "") + " " + (c.get("lastName") or "")).strip() or c.get("email", ""),
            "email": c.get("email", ""),
            "dateAdded": c.get("dateAdded"),
        })

    # Wzbogacenie o Meta data
    for ad_id, row in per_ad.items():
        meta_meta = meta_ad_map.get(ad_id, {})
        ins = meta_ad_insights.get(ad_id, {})
        row["ad_name"] = meta_meta.get("name", ad_id)
        row["meta_campaign_id"] = meta_meta.get("campaign_id")
        row["spend"] = float(ins.get("spend", 0) or 0) if ins else 0.0
        row["meta_leads_reported"] = sum(int(float(a.get("value", 0))) for a in (ins.get("actions") or []) if a.get("action_type") == "offsite_conversion.fb_pixel_custom") if ins else 0
        row["real_cpl"] = (row["spend"] / row["leads"]) if row["leads"] else None
        row["real_cpb"] = (row["spend"] / row["bookings"]) if row["bookings"] else None

    # Per-campaign aggregation
    per_campaign = {}
    for ad_id, row in per_ad.items():
        cid = row.get("meta_campaign_id") or "(unknown)"
        if cid not in per_campaign:
            per_campaign[cid] = {
                "campaign_id": cid,
                "campaign_name": meta_campaign_meta.get(cid, {}).get("name", cid),
                "spend": 0.0,
                "leads": 0,
                "bookings": 0,
                "sales": 0,
                "revenue_pln": 0.0,
                "ad_count": 0,
            }
        # spend liczymy z campaign-level insights (NIE sumujemy z ad-level — bo ady mogą być z innej kampanii)
        per_campaign[cid]["leads"] += row["leads"]
        per_campaign[cid]["bookings"] += row["bookings"]
        per_campaign[cid]["sales"] += row["sales"]
        per_campaign[cid]["revenue_pln"] += row.get("revenue_pln", 0.0)
        per_campaign[cid]["ad_count"] += 1

    # Spend per campaign — z meta_campaign_insights
    for cid, row in per_campaign.items():
        ins = meta_campaign_insights.get(cid, {})
        row["spend"] = float(ins.get("spend", 0) or 0) if ins else 0.0
        row["real_cpl"] = (row["spend"] / row["leads"]) if row["leads"] else None
        row["real_cpb"] = (row["spend"] / row["bookings"]) if row["bookings"] else None

    # Bookings dziś (z calendar_events i opportunities z lastStageChangeAt = today)
    bookings_today = []
    for o in opportunities:
        sid = o.get("pipelineStageId") or o.get("pipelineStageUId")
        info = stage_map.get(sid, {})
        if info.get("stage_name") not in BOOKING_STAGES:
            continue
        change = parse_iso(o.get("lastStageChangeAt", ""))
        if change and change.date().isoformat() == target_date:
            bookings_today.append(o)

    return {
        "target_date": target_date,
        "all_contacts_today": len(all_today),
        "real_leads_today": len(contacts_today),
        "ig_sync_ghosts": len(ghosts_today),
        "paid_contacts": len(paid_contacts),
        "organic_contacts": len(organic_contacts),
        "other_contacts": len(other_contacts),
        "per_ad": list(per_ad.values()),
        "per_campaign": list(per_campaign.values()),
        "bookings_today": bookings_today,
        "stage_map": stage_map,
    }
