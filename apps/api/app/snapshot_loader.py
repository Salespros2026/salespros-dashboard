"""Czyta najnowsze snapshoty Meta + GHL z dysku jako fallback / sanity check."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .deps import get_settings

log = logging.getLogger("snapshot_loader")


def _list_meta_snapshots(snap_dir: Path) -> list[Path]:
    """Meta snapshot ma nazwę `YYYY-MM-DD.json` (bez prefix).
    Wykluczamy ghl-*, insights-*, historical_*, *.bak.* — to są inne pliki które tu się znalazły.
    """
    EXCLUDED_PREFIXES = ("ghl-", "insights-", "historical_")
    return sorted(
        [
            p for p in snap_dir.glob("*.json")
            if not p.name.startswith(EXCLUDED_PREFIXES) and ".bak." not in p.name
        ],
        reverse=True,
    )


def _list_ghl_snapshots(snap_dir: Path) -> list[Path]:
    return sorted(
        [p for p in snap_dir.glob("ghl-*.json") if ".bak." not in p.name],
        reverse=True,
    )


def load_meta_snapshot(target_date: Optional[str] = None) -> Optional[dict]:
    s = get_settings()
    if not s.snapshots_path:
        return None
    snap_dir = s.snapshots_path
    if target_date:
        p = snap_dir / f"{target_date}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    files = _list_meta_snapshots(snap_dir)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def load_ghl_snapshot() -> Optional[dict]:
    """GHL snapshot zawiera ostatnie 14 dni — bierzemy najnowszy."""
    s = get_settings()
    if not s.snapshots_path:
        return None
    files = _list_ghl_snapshots(s.snapshots_path)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def load_meta_snapshots_range(from_date: str, to_date: str) -> list[dict]:
    """Zwraca listę snapshotów dla każdej daty w zakresie (jeśli istnieje na dysku)."""
    s = get_settings()
    if not s.snapshots_path:
        return []
    snap_dir = s.snapshots_path
    out: list[dict] = []
    files_by_date = {p.stem: p for p in _list_meta_snapshots(snap_dir)}
    from datetime import date, timedelta
    d = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    while d <= end:
        p = files_by_date.get(d.isoformat())
        if p:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:
                log.warning("Cannot parse %s: %s", p, e)
        d += timedelta(days=1)
    return out
