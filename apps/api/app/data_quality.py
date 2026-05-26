"""Walidacja snapshotów Meta / GHL przed agregacją.

Bez tego pipeline cache'ował "ładne zera" gdy Meta/GHL zwracały 200 OK z pustą zawartością
(np. soft-expired token, rate limit zwracający pustą listę). Dashboard udawał wtedy
"normalny dzień bez ruchu". Teraz takie sytuacje wracają z `data_quality_issues` zamiast
cache hitu, a aggregation może spróbować fallbacku do snapshot z dysku.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataQualityResult:
    ok: bool
    issues: list[str]


def validate_meta_snapshot(meta: dict | None) -> DataQualityResult:
    issues: list[str] = []
    if not meta:
        return DataQualityResult(ok=False, issues=["meta_missing"])
    insights = meta.get("insights") or {}
    for level in ("account", "campaign", "ad"):
        if level not in insights:
            issues.append(f"meta_missing_insights_{level}")
    if all(not insights.get(level) for level in ("account", "campaign", "ad")):
        issues.append("meta_all_insights_empty")
    if not meta.get("account_info"):
        issues.append("meta_missing_account_info")
    return DataQualityResult(ok=not issues, issues=issues)


def validate_ghl_snapshot(ghl: dict | None) -> DataQualityResult:
    issues: list[str] = []
    if not ghl:
        return DataQualityResult(ok=False, issues=["ghl_missing"])
    for key in ("contacts", "pipelines", "opportunities", "calendar_events"):
        if not isinstance(ghl.get(key), list):
            issues.append(f"ghl_invalid_{key}")
    return DataQualityResult(ok=not issues, issues=issues)
