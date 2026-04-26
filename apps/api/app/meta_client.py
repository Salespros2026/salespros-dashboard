"""Meta Ads API client (live).

Używa facebook_business SDK. Dla insights pobiera level=campaign|adset|ad,
time_range = {since, until} w timezone konta (Europe/Warsaw — to ad account TZ).
"""
from __future__ import annotations

import logging
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi

from .deps import get_settings

log = logging.getLogger("meta_client")

_INSIGHT_FIELDS = [
    "spend", "impressions", "reach", "clicks", "ctr", "cpc", "cpm",
    "frequency", "actions", "cost_per_action_type",
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
    return _to_dict(acct.api_get(fields=[
        "id", "name", "currency", "balance", "amount_spent", "timezone_name",
        "account_status", "spend_cap",
    ]))


def fetch_campaigns() -> list[dict]:
    acct = _account()
    cursor = acct.get_campaigns(fields=_CAMPAIGN_FIELDS, params={"limit": 200})
    return [_to_dict(c) for c in cursor]


def fetch_adsets() -> list[dict]:
    acct = _account()
    cursor = acct.get_ad_sets(fields=_ADSET_FIELDS, params={"limit": 500})
    return [_to_dict(a) for a in cursor]


def fetch_ads() -> list[dict]:
    acct = _account()
    cursor = acct.get_ads(fields=_AD_FIELDS, params={"limit": 1000})
    return [_to_dict(a) for a in cursor]


def fetch_insights(level: str, since: str, until: str) -> list[dict]:
    """level: 'account' | 'campaign' | 'adset' | 'ad'."""
    acct = _account()
    params = {
        "level": level,
        "time_range": {"since": since, "until": until},
        "time_increment": "all_days",
        "limit": 1000,
    }
    cursor = acct.get_insights(fields=_INSIGHT_FIELDS, params=params)
    return [_to_dict(r) for r in cursor]


def fetch_insights_daily(level: str, since: str, until: str) -> list[dict]:
    """Z time_increment=1 (per dzień) — dla trend charts."""
    acct = _account()
    params = {
        "level": level,
        "time_range": {"since": since, "until": until},
        "time_increment": 1,
        "limit": 1000,
    }
    cursor = acct.get_insights(fields=_INSIGHT_FIELDS + ["date_start", "date_stop"], params=params)
    return [_to_dict(r) for r in cursor]


def fetch_creative(creative_id: str) -> dict:
    from facebook_business.adobjects.adcreative import AdCreative
    _api()
    return _to_dict(AdCreative(creative_id).api_get(fields=_CREATIVE_FIELDS))


def fetch_creatives_by_ad_id(ad_ids: list[str]) -> dict[str, dict]:
    """Dla każdego ad_id pobiera jego creative metadata."""
    from facebook_business.adobjects.ad import Ad
    _api()
    out: dict[str, dict] = {}
    for ad_id in ad_ids:
        try:
            ad = Ad(ad_id).api_get(fields=["creative"])
            cid = (ad.get("creative") or {}).get("id")
            if cid:
                out[ad_id] = fetch_creative(cid)
        except Exception as e:
            log.warning("Creative fetch failed for ad %s: %s", ad_id, e)
    return out


def build_meta_snapshot_like(since: str, until: str) -> dict:
    """Buduje strukturę zgodną z `snapshots/YYYY-MM-DD.json` żeby reuse-ować attribution.py
    bez modyfikacji."""
    account_info = fetch_account_info()
    campaigns = fetch_campaigns()
    adsets = fetch_adsets()
    ads = fetch_ads()
    insights = {
        "account": fetch_insights("account", since, until),
        "campaign": fetch_insights("campaign", since, until),
        "adset": fetch_insights("adset", since, until),
        "ad": fetch_insights("ad", since, until),
    }
    ad_ids = [a["id"] for a in ads]
    # Creatives — pobieramy tylko dla adów które miały spend (oszczędność rate limitu)
    spending_ad_ids = {ins.get("ad_id") for ins in insights["ad"] if float(ins.get("spend", 0) or 0) > 0}
    creatives_by_ad_id = fetch_creatives_by_ad_id(list(spending_ad_ids))
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
