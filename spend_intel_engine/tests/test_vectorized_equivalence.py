"""Validate vectorized daily scoring matches legacy loop logic for baseline mode."""
from __future__ import annotations

from datetime import date
from typing import Any, List

from spend_intel_engine.domain.models import RuleMaps, ShoppingCfg, SpendProfile
from spend_intel_engine.scoring.daily_scorer import score_daily_shopping
from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code, symmetric_keys
from spend_intel_engine.utils.dates import daterange_inclusive, parse_iso_date, proximity_factor
from spend_intel_engine.utils.numbers import to_int_score


class SampleLifeEvent:
    def __init__(
        self,
        aspect: str,
        aspectNature: str,
        startDate: str,
        endDate: str,
        exactDate: str,
        eventType: str,
        description: str,
    ) -> None:
        self.aspect = aspect
        self.aspectNature = aspectNature
        self.startDate = startDate
        self.endDate = endDate
        self.exactDate = exactDate
        self.eventType = eventType
        self.description = description


def _legacy_daily_scores(
    life_events: List[Any],
    start_date: date,
    n_days: int,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
) -> List[int]:
    end_date = start_date.fromordinal(start_date.toordinal() + n_days - 1)
    deltas = {d: 0.0 for d in daterange_inclusive(start_date, end_date)}

    for event in life_events:
        norm = normalize_aspect_code(str(getattr(event, "aspect", "")))
        if not norm:
            continue

        start = parse_iso_date(str(getattr(event, "startDate", "")))
        end = parse_iso_date(str(getattr(event, "endDate", "")))
        exact = parse_iso_date(str(getattr(event, "exactDate", "")))

        active_start = max(start, start_date)
        active_end = min(end, end_date)
        if active_start > active_end:
            continue

        direct, reverse = symmetric_keys(norm)
        asp_type = direct.split()[1]
        asp_weight = cfg.aspect_type_weights.get(asp_type, 0.8)
        ev_type = str(getattr(event, "eventType", "MINOR")).upper()
        weight = cfg.event_type_weights.get(ev_type, cfg.minor_event_weight)
        amplitude = cfg.major_amplitude if ev_type == "MAJOR" else cfg.minor_amplitude
        polarity = 1.0 if str(getattr(event, "aspectNature", "Negative")).lower() == "positive" else -1.0

        span_len = (end - start).days + 1
        for day in daterange_inclusive(active_start, active_end):
            prox = proximity_factor(day, exact, span_len)
            contribution = polarity * weight * asp_weight * prox * amplitude
            deltas[day] += contribution

    out: List[int] = []
    for day in daterange_inclusive(start_date, end_date):
        out.append(to_int_score(cfg.daily_base_score + deltas[day], 0, 100))
    return out


def test_vectorized_scoring_matches_legacy_baseline() -> None:
    cfg = ShoppingCfg(
        purchase_type="big_ticket",
        moon_trigger_enabled=False,
        natal_spend_aspects_csv="a.csv",
        transit_daily_shopping_aspects_csv="b.csv",
        natal_structure_signals_csv="c.csv",
        moon_spending_aspects_csv="d.csv",
    )
    profile = SpendProfile(score=50, category="Balanced", description="", top_drivers=[])
    rules = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={
            "JUP SEX MAR": "supports planned buying",
            "VEN SQR SAT": "constraint pressure",
        },
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="x",
    )

    events = [
        SampleLifeEvent("Jup Sxt Mar", "Positive", "2026-02-20", "2026-02-24", "2026-02-22", "MAJOR", "good"),
        SampleLifeEvent("Ven Sqr Sat", "Negative", "2026-02-21", "2026-02-25", "2026-02-23", "MINOR", "tight"),
    ]

    vectorized = score_daily_shopping(
        events,
        start_date=date(2026, 2, 20),
        n_days=6,
        profile=profile,
        rule_maps=rules,
        cfg=cfg,
    )
    legacy = _legacy_daily_scores(events, date(2026, 2, 20), 6, rules, cfg)

    assert [d.score for d in vectorized] == legacy
