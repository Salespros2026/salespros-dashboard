"""Klasyfikator kampanii: acquisition vs retarget vs unknown.

Priorytet: manual override > name_contains > objective_fallback > "unknown".
Stan persistowany w JSON (CLASSIFICATION_FILE_PATH).
Czytamy z file-mtime cache, zapisujemy atomically (tmp+rename).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Literal

from .deps import get_settings

log = logging.getLogger("classifier")

CampaignType = Literal["acquisition", "retarget", "unknown"]
VALID_TYPES: set[str] = {"acquisition", "retarget"}

_DEFAULT_STATE = {
    "auto_rules": {"name_contains": {}, "objective_fallback": {}},
    "manual": {},
}

_lock = RLock()
_cache: dict | None = None
_cache_mtime: float | None = None


def _path() -> Path:
    s = get_settings()
    return Path(s.CLASSIFICATION_FILE_PATH).expanduser()


def _load_state() -> dict:
    global _cache, _cache_mtime
    p = _path()
    with _lock:
        if not p.exists():
            log.warning("Classification file missing at %s — using empty state", p)
            return dict(_DEFAULT_STATE)
        mtime = p.stat().st_mtime
        if _cache is not None and _cache_mtime == mtime:
            return _cache
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.error("Cannot parse %s: %s — falling back to empty state", p, e)
            return dict(_DEFAULT_STATE)
        data.setdefault("auto_rules", {}).setdefault("name_contains", {})
        data["auto_rules"].setdefault("objective_fallback", {})
        data.setdefault("manual", {})
        _cache = data
        _cache_mtime = mtime
        return data


def _save_state(state: dict) -> None:
    global _cache, _cache_mtime
    p = _path()
    with _lock:
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=p.parent, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, p)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        _cache = state
        _cache_mtime = p.stat().st_mtime


def _classify_by_rules(name: str, objective: str, state: dict) -> CampaignType:
    rules = state.get("auto_rules") or {}
    name_lc = (name or "").lower()
    for keyword, ctype in (rules.get("name_contains") or {}).items():
        if keyword.lower() in name_lc and ctype in VALID_TYPES:
            return ctype  # type: ignore[return-value]
    obj_map = rules.get("objective_fallback") or {}
    if objective and objective in obj_map and obj_map[objective] in VALID_TYPES:
        return obj_map[objective]  # type: ignore[return-value]
    return "unknown"


def classify_campaign(campaign: dict) -> CampaignType:
    """Zwraca typ kampanii dla danego campaign dict (z Meta API).
    Pola wymagane: 'id' lub 'campaign_id', 'name' / 'campaign_name', 'objective'.
    """
    state = _load_state()
    cid = str(campaign.get("id") or campaign.get("campaign_id") or "")
    manual = state.get("manual") or {}
    if cid and cid in manual and manual[cid] in VALID_TYPES:
        return manual[cid]
    name = campaign.get("name") or campaign.get("campaign_name") or ""
    objective = campaign.get("objective") or ""
    return _classify_by_rules(name, objective, state)


def suggest_for(campaign: dict) -> CampaignType:
    """Sugestia auto-rule pomijając manual override (do panelu admin)."""
    state = _load_state()
    name = campaign.get("name") or campaign.get("campaign_name") or ""
    objective = campaign.get("objective") or ""
    return _classify_by_rules(name, objective, state)


def is_manual(campaign_id: str) -> bool:
    state = _load_state()
    return campaign_id in (state.get("manual") or {})


def set_manual(campaign_id: str, ctype: str) -> None:
    if ctype not in VALID_TYPES:
        raise ValueError(f"Invalid campaign type: {ctype}. Must be one of {VALID_TYPES}")
    state = _load_state()
    manual = dict(state.get("manual") or {})
    manual[str(campaign_id)] = ctype
    state["manual"] = manual
    _save_state(state)


def clear_manual(campaign_id: str) -> None:
    state = _load_state()
    manual = dict(state.get("manual") or {})
    if str(campaign_id) in manual:
        manual.pop(str(campaign_id))
        state["manual"] = manual
        _save_state(state)
