"""Meta Ads API client (live).

Używa facebook_business SDK. Dla insights pobiera level=campaign|adset|ad,
time_range = {since, until} w timezone konta (Europe/Warsaw — to ad account TZ).

Circuit breaker: gdy Meta zwróci error code=17/subcode=2446079 (Ad-Account-Level
Rate Limit), arming na N sekund — kolejne calle podnoszą `MetaRateLimited` od razu,
bez bicia Meta. Pozwala aggregation.py spokojnie spaść na snapshot zamiast spamować.

Creative cache: metadata (thumbnail/title/body) keszowane w pamięci na 24h per
creative_id — fetch_creatives_by_ad_id pobiera tylko brakujące. Wcześniej każdy
/api/creatives request bił Meta po 2 calle per spending ad (50+ calli na 25 adów).
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

from .deps import get_settings

log = logging.getLogger("meta_client")


# ===== Circuit breaker (ad-account-level rate limit) =====

class MetaRateLimited(Exception):
    """Podniesione gdy circuit breaker jest armed po code=17/subcode=2446079."""


_RATE_LIMIT_CODE = 17
_RATE_LIMIT_SUBCODE = 2446079
_RATE_LIMIT_COOLDOWN_S = 3600  # 1h — Meta zwykle resetuje szybciej, ale daje bufor

_rate_limit_lock = threading.Lock()
_rate_limit_until: float = 0.0  # epoch seconds; 0 = no active cooldown


def _check_rate_limit() -> None:
    """Raise MetaRateLimited jeśli circuit breaker armed."""
    now = time.time()
    with _rate_limit_lock:
        if _rate_limit_until > now:
            remaining = int(_rate_limit_until - now)
            raise MetaRateLimited(
                f"Meta ad-account rate limit cooldown — {remaining}s remaining"
            )


def _arm_circuit_breaker(fbtrace_id: str | None) -> None:
    global _rate_limit_until
    with _rate_limit_lock:
        _rate_limit_until = time.time() + _RATE_LIMIT_COOLDOWN_S
    log.error(
        "Meta rate limit hit (code=%s/subcode=%s, fbtrace=%s). Circuit breaker armed for %ds.",
        _RATE_LIMIT_CODE, _RATE_LIMIT_SUBCODE, fbtrace_id, _RATE_LIMIT_COOLDOWN_S,
    )


def _handle_fb_error(e: FacebookRequestError) -> None:
    """Loguje + arm circuit breaker jeśli to rate limit. Zawsze re-raise."""
    code = e.api_error_code()
    subcode = e.api_error_subcode()
    msg = e.api_error_message()
    fbtrace = None
    try:
        body = e.body() or {}
        fbtrace = (body.get("error") or {}).get("fbtrace_id")
    except Exception:
        pass
    if code == _RATE_LIMIT_CODE and subcode == _RATE_LIMIT_SUBCODE:
        _arm_circuit_breaker(fbtrace)
    else:
        log.error(
            "Meta API error: code=%s subcode=%s msg=%s fbtrace=%s",
            code, subcode, msg, fbtrace,
        )


def _fb_call(fn, *args, **kwargs):
    """Wrapper: check breaker → call → on FacebookRequestError, arm breaker + re-raise."""
    _check_rate_limit()
    try:
        return fn(*args, **kwargs)
    except FacebookRequestError as e:
        _handle_fb_error(e)
        raise


# ===== Creative metadata cache (24h TTL) =====

_CREATIVE_CACHE_TTL_S = 24 * 3600
_creative_cache_lock = threading.Lock()
_creative_cache: dict[str, tuple[dict, float]] = {}  # creative_id → (data, fetched_at)


def _creative_cache_get(creative_id: str) -> dict | None:
    now = time.time()
    with _creative_cache_lock:
        hit = _creative_cache.get(creative_id)
        if hit and (now - hit[1]) < _CREATIVE_CACHE_TTL_S:
            return hit[0]
    return None


def _creative_cache_put(creative_id: str, data: dict) -> None:
    with _creative_cache_lock:
        _creative_cache[creative_id] = (data, time.time())

_INSIGHT_FIELDS = [
    "spend", "impressions", "reach", "clicks", "ctr", "cpc", "cpm",
    "frequency", "actions", "cost_per_action_type",
    "inline_link_clicks",  # link clicks (vs all clicks)
    # Video metrics — Meta nie ma osobnych pól dla 3sec/15sec view; 3-sec views są w
    # actions[].action_type='video_view'. Hold rate liczymy z p50/p25 jako proxy retention.
    "video_thruplay_watched_actions",  # 15s lub 97% — Meta default
    "video_p25_watched_actions", "video_p50_watched_actions",
    "video_p75_watched_actions", "video_p100_watched_actions",
    "ad_id", "ad_name", "adset_id", "adset_name", "campaign_id", "campaign_name",
]

_AD_FIELDS = [
    "id", "name", "status", "effective_status", "campaign_id", "adset_id",
    "creative", "created_time", "updated_time",
]
_ADSET_FIELDS = [
    "id", "name", "status", "effective_status", "campaign_id",
    "optimization_goal", "billing_event", "daily_budget", "lifetime_budget",
    "targeting",
]
_CAMPAIGN_FIELDS = [
    "id", "name", "status", "effective_status", "objective",
    "daily_budget", "lifetime_budget", "buying_type", "created_time",
]
_CREATIVE_FIELDS = [
    "id", "name", "title", "body", "image_url", "thumbnail_url",
    "video_id", "object_story_spec", "call_to_action_type",
]


def _api():
    s = get_settings()
    return FacebookAdsApi.init(access_token=s.META_ACCESS_TOKEN)


def _account() -> AdAccount:
    s = get_settings()
    _api()
    return AdAccount(s.META_AD_ACCOUNT_ID)


def _to_dict(obj: Any) -> dict:
    if hasattr(obj, "export_all_data"):
        return obj.export_all_data()
    return dict(obj) if obj else {}


def fetch_account_info() -> dict:
    s = get_settings()
    _api()
    acct = AdAccount(s.META_AD_ACCOUNT_ID)
    return _fb_call(
        lambda: _to_dict(acct.api_get(fields=[
            "id", "name", "currency", "balance", "amount_spent", "timezone_name",
            "account_status", "spend_cap",
        ]))
    )


def fetch_campaigns() -> list[dict]:
    acct = _account()
    def _do():
        cursor = acct.get_campaigns(fields=_CAMPAIGN_FIELDS, params={"limit": 200})
        return [_to_dict(c) for c in cursor]
    return _fb_call(_do)


def fetch_adsets() -> list[dict]:
    acct = _account()
    def _do():
        cursor = acct.get_ad_sets(fields=_ADSET_FIELDS, params={"limit": 500})
        return [_to_dict(a) for a in cursor]
    return _fb_call(_do)


def fetch_ads() -> list[dict]:
    acct = _account()
    def _do():
        cursor = acct.get_ads(fields=_AD_FIELDS, params={"limit": 1000})
        return [_to_dict(a) for a in cursor]
    return _fb_call(_do)


def fetch_insights(level: str, since: str, until: str) -> list[dict]:
    """level: 'account' | 'campaign' | 'adset' | 'ad'."""
    acct = _account()
    params = {
        "level": level,
        "time_range": {"since": since, "until": until},
        "time_increment": "all_days",
        "limit": 1000,
    }
    def _do():
        cursor = acct.get_insights(fields=_INSIGHT_FIELDS, params=params)
        return [_to_dict(r) for r in cursor]
    return _fb_call(_do)


def fetch_insights_daily(level: str, since: str, until: str) -> list[dict]:
    """Z time_increment=1 (per dzień) — dla trend charts."""
    acct = _account()
    params = {
        "level": level,
        "time_range": {"since": since, "until": until},
        "time_increment": 1,
        "limit": 1000,
    }
    def _do():
        cursor = acct.get_insights(fields=_INSIGHT_FIELDS + ["date_start", "date_stop"], params=params)
        return [_to_dict(r) for r in cursor]
    return _fb_call(_do)


def fetch_creative(creative_id: str) -> dict:
    """Pobiera metadata kreacji. Cache 24h — kreacje rzadko się zmieniają."""
    cached = _creative_cache_get(creative_id)
    if cached is not None:
        return cached
    from facebook_business.adobjects.adcreative import AdCreative
    _api()
    data = _fb_call(lambda: _to_dict(AdCreative(creative_id).api_get(fields=_CREATIVE_FIELDS)))
    _creative_cache_put(creative_id, data)
    return data


def _fetch_one_creative_for_ad(ad_id: str) -> tuple[str, dict | None]:
    """Pobiera creative_id z ad metadata, potem creative. Honoruje circuit breaker."""
    from facebook_business.adobjects.ad import Ad
    try:
        _check_rate_limit()
        ad = _fb_call(lambda: Ad(ad_id).api_get(fields=["creative"]))
        cid = (ad.get("creative") or {}).get("id")
        if cid:
            return ad_id, fetch_creative(cid)
    except MetaRateLimited:
        # Don't spam logs — fast-fail through.
        raise
    except Exception as e:
        log.warning("Creative fetch failed for ad %s: %s", ad_id, e)
    return ad_id, None


def fetch_creatives_by_ad_id(
    ad_ids: list[str],
    ads_meta: list[dict] | None = None,
) -> dict[str, dict]:
    """Dla każdego ad_id pobiera jego creative metadata.

    Optymalizacja: jeśli ads_meta jest podane (lista ze `_AD_FIELDS`), używamy creative_id
    bezpośrednio z metadanych adów — oszczędza N callsów `Ad(ad_id).api_get(fields=['creative'])`.
    Plus cache creative metadata 24h.
    """
    _api()
    out: dict[str, dict] = {}
    if not ad_ids:
        return out

    creative_id_by_ad: dict[str, str] = {}
    if ads_meta:
        ad_by_id = {a.get("id"): a for a in ads_meta if a.get("id")}
        for aid in ad_ids:
            cid = ((ad_by_id.get(aid) or {}).get("creative") or {}).get("id")
            if cid:
                creative_id_by_ad[aid] = cid

    # Krok 1: dla adów BEZ creative_id w metadanych — pobieramy Ad() (jeden call każdy).
    missing = [aid for aid in ad_ids if aid not in creative_id_by_ad]
    if missing:
        from facebook_business.adobjects.ad import Ad
        def _fetch_creative_id(aid: str) -> tuple[str, str | None]:
            try:
                _check_rate_limit()
                ad = _fb_call(lambda: Ad(aid).api_get(fields=["creative"]))
                cid = (ad.get("creative") or {}).get("id")
                return aid, cid
            except MetaRateLimited:
                raise
            except Exception as e:
                log.warning("Ad metadata fetch failed for %s: %s", aid, e)
                return aid, None
        try:
            with ThreadPoolExecutor(max_workers=10) as ex:
                for aid, cid in ex.map(_fetch_creative_id, missing):
                    if cid:
                        creative_id_by_ad[aid] = cid
        except MetaRateLimited:
            # Pozwól górnym warstwom obsłużyć — nie kontynuuj fetchu creativów.
            raise

    # Krok 2: fetch creative metadata (z cache 24h — większość trafia w cache).
    def _fetch_creative_safe(item: tuple[str, str]) -> tuple[str, dict | None]:
        aid, cid = item
        try:
            return aid, fetch_creative(cid)
        except MetaRateLimited:
            raise
        except Exception as e:
            log.warning("Creative fetch failed for %s (creative=%s): %s", aid, cid, e)
            return aid, None

    items = list(creative_id_by_ad.items())
    if not items:
        return out
    try:
        with ThreadPoolExecutor(max_workers=10) as ex:
            for aid, creative in ex.map(_fetch_creative_safe, items):
                if creative is not None:
                    out[aid] = creative
    except MetaRateLimited:
        raise
    return out


def build_meta_snapshot_like(since: str, until: str, full: bool = False) -> dict:
    """Buduje strukturę zgodną z `snapshots/YYYY-MM-DD.json`.

    full=False (default): pobiera tylko insights (account/campaign/ad) + campaigns.
      Wystarczy dla overview, campaigns, funnel. Oszczędza rate limit.
    full=True: pobiera też adsets, ads×1000, creatives.
      Potrzebne dla /adsets i /creatives.
    """
    levels = ["account", "campaign", "adset", "ad"]
    with ThreadPoolExecutor(max_workers=6) as ex:
        account_info_fut = ex.submit(fetch_account_info)
        campaigns_fut = ex.submit(fetch_campaigns)
        insights_futs = {lvl: ex.submit(fetch_insights, lvl, since, until) for lvl in levels}
        if full:
            adsets_fut = ex.submit(fetch_adsets)
            ads_fut = ex.submit(fetch_ads)

        account_info = account_info_fut.result()
        campaigns = campaigns_fut.result()
        insights = {lvl: f.result() for lvl, f in insights_futs.items()}

        if full:
            adsets = adsets_fut.result()
            ads = ads_fut.result()
            spending_ad_ids = {ins.get("ad_id") for ins in insights["ad"] if float(ins.get("spend", 0) or 0) > 0}
            # ads_meta=ads → użyje creative_id z metadanych zamiast 1 callu Meta per ad.
            # Plus _creative_cache trzyma metadane 24h. Łącznie: ~25 calli → 0-3 calli.
            creatives_by_ad_id = fetch_creatives_by_ad_id(
                list(spending_ad_ids), ads_meta=ads,
            )
        else:
            adsets = []
            ads = []
            creatives_by_ad_id = {}

    return {
        "snapshot_date": until,
        "ad_account_id": account_info.get("id"),
        "account_info": account_info,
        "campaigns": campaigns,
        "adsets": adsets,
        "ads": ads,
        "insights": insights,
        "creatives_by_ad_id": creatives_by_ad_id,
    }
