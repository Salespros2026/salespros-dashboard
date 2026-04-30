"""Creative Health Score 0-100.

Composite z 5 metryk wg `wiedza/creative-rules.md` sekcja 2:
- 40% CPL vs target
- 20% Hook rate (3-sec / impressions) vs baseline 30%
- 15% Hold rate (15-sec / 3-sec) vs baseline 50%
- 15% CTR (link) vs baseline 1.5%
- 10% Frequency penalty (od 2.5)

Gatekeeper: kreacja musi mieć spend >= 3× target_CPL żeby dostać score.
Inaczej zwracamy None + status="insufficient" ("za mało danych").

Targety z `workspace/marketing/kampanie płatne Salespros/konfiguracja/target-kpi.md`:
- target_cpl = 40 PLN (booked rozmowa, ambitne ale realistyczne dla EDU PL)
- hook_rate target = 25%, baseline scoring = 30% (nieco bardziej rygorystycznie)
- hold_rate target = 50%
- CTR link target = 1.5%
- frequency warn > 2.5
"""
from __future__ import annotations

# Defaulty z konfiguracja/target-kpi.md
DEFAULT_TARGETS = {
    "cpl": 40.0,                    # PLN — target CPL booked rozmowy
    "hook_rate": 0.30,              # 30% baseline (target z target-kpi to 25%, ale 30% jako "good")
    "hold_rate": 0.50,              # 50% baseline
    "ctr_link": 0.015,              # 1.5% baseline
    "frequency_warn": 2.5,
    "min_spend_for_score": 120.0,   # 3× target_CPL
}


def compute_health_score(
    *,
    spend: float,
    real_cpl: float | None,
    hook_rate: float | None,
    hold_rate: float | None,
    ctr: float | None,           # CTR jako % (np. 1.5 oznacza 1.5%)
    frequency: float | None,
    targets: dict | None = None,
) -> tuple[int | None, str]:
    """Returns (score 0-100 or None, status).

    Status: 'winner' | 'average' | 'loser' | 'insufficient'
    """
    t = {**DEFAULT_TARGETS, **(targets or {})}

    if spend < t["min_spend_for_score"]:
        return None, "insufficient"

    # Score components (każdy capped na 1.5 = "ekstremalnie dobre" → bonus do 50%)
    if real_cpl and real_cpl > 0:
        cpl_score = min(t["cpl"] / real_cpl, 1.5)
    else:
        cpl_score = 0.0  # brak leadów to score=0 dla CPL składowej

    hook_score = min(hook_rate / t["hook_rate"], 1.5) if hook_rate else 0.5  # neutral fallback
    hold_score = min(hold_rate / t["hold_rate"], 1.5) if hold_rate else 0.5
    # CTR z Meta API jest jako %, np. 1.234 oznacza 1.234%. Konwertuj na ułamek przed porównaniem.
    if ctr and ctr > 0:
        ctr_decimal = ctr / 100.0
        ctr_score = min(ctr_decimal / t["ctr_link"], 1.5)
    else:
        ctr_score = 0.0

    # Frequency penalty: 1.0 do 2.5, potem liniowo do 0 przy 4.0
    if frequency is not None:
        freq_penalty = max(0.0, 1.0 - max(0.0, (frequency - t["frequency_warn"]) / 1.5))
    else:
        freq_penalty = 1.0  # brak frequency = nie karz

    composite = (
        0.40 * cpl_score
        + 0.20 * hook_score
        + 0.15 * hold_score
        + 0.15 * ctr_score
        + 0.10 * freq_penalty
    )
    # Normalize: max possible = 0.40*1.5 + 0.20*1.5 + 0.15*1.5 + 0.15*1.5 + 0.10*1.0 = 1.45
    # Skalujemy do 0-100 dzieląc przez 1.45 (a nie 1.5) żeby score 100 było faktycznie osiągalne
    score = int(round(100 * composite / 1.45))
    score = max(0, min(100, score))

    if score >= 80:
        status = "winner"
    elif score >= 50:
        status = "average"
    else:
        status = "loser"
    return score, status
