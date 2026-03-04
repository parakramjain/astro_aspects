from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List, Literal, Tuple, overload

import numpy as np
import pandas as pd

from spend_intel_engine.domain.enums import BASE_AMPLITUDE, RISK_MULTIPLIER
from spend_intel_engine.domain.models import DailyScore, Driver, RuleMaps, ShoppingCfg, SpendProfile
from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code, symmetric_keys
from spend_intel_engine.utils.dates import daterange_inclusive, parse_iso_date
from spend_intel_engine.utils.numbers import clamp, to_int_score

# Hard aspects that receive additional scrutiny
HARD_ASPECTS = {"SQR", "OPP"}

# Outer planets for luxury penalty
OUTER_PLANETS = {"NEP", "URA", "PLU"}


def _numeric_proximity(current_idx: int, exact_idx: int, span_len: int) -> float:
    denominator = max(1, span_len)
    distance = abs(current_idx - exact_idx)
    return clamp(1.0 - min(distance / denominator, 1.0), 0.0, 1.0)


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    return getattr(obj, key, default)


def _aspect_type(aspect_key: str) -> str:
    parts = aspect_key.split()
    return parts[1] if len(parts) == 3 else "CON"


def _event_weight(event_type: str, cfg: ShoppingCfg) -> float:
    return cfg.event_type_weights.get(str(event_type or "").upper(), cfg.minor_event_weight)


def _amplitude(event_type: str, cfg: ShoppingCfg) -> float:
    if str(event_type or "").upper() == "MAJOR":
        return cfg.major_amplitude
    return cfg.minor_amplitude


def _polarity(aspect_nature: str) -> float:
    return 1.0 if str(aspect_nature or "").lower() == "positive" else -1.0


def _has_outer_planet_hard_aspect(aspect_key: str) -> bool:
    """Check if aspect involves outer planet with hard aspect."""
    parts = aspect_key.split()
    if len(parts) != 3:
        return False
    left, asp_type, right = parts
    return asp_type in HARD_ASPECTS and (left in OUTER_PLANETS or right in OUTER_PLANETS)


def _get_purchase_advice(purchase_type: str) -> str:
    """Get purchase-specific advice based on type."""
    advice = {
        "essentials": "Safe for routine or necessary spending.",
        "big_ticket": "Ensure planning and comparison before committing.",
        "luxury": "Apply budget cap and cooling-off rule.",
    }
    return advice.get(purchase_type, "")


def _build_note(
    score: int,
    strongest: Driver | None,
    profile: SpendProfile,
    purchase_type: str,
) -> str:
    if strongest and strongest.weight > 0:
        note = "Good climate for planned buys; compare prices before checkout."
    elif strongest and strongest.weight < 0:
        note = "Impulse risk elevated; delay non-essential purchases and verify terms."
    else:
        note = "Mixed signals; stick to priority items and avoid rushed decisions."

    if profile.category == "Impulsive/High-Spend Risk":
        note = f"{note} Keep a hard budget cap."
    
    # Append purchase-specific advice
    advice = _get_purchase_advice(purchase_type)
    if advice:
        note = f"{note} {advice}"

    return note[:200]


def _preprocess_events(
    life_events: List[Any],
    start_date: date,
    end_date: date,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
) -> pd.DataFrame:
    """Convert life events into structured dataframe for vectorized processing.
    
    Returns DataFrame with columns:
        - event_index: int
        - polarity: float (+1 or -1)
        - amplitude: float
        - start_index: int (days from start_date)
        - end_index: int (days from start_date)
        - exact_index: int (days from start_date)
        - aspect_key: str
        - implication: str
        - is_mapped: bool
        - is_major: bool
        - is_moon: bool
        - is_hard_aspect: bool
        - has_outer_planet: bool
    """
    rows = []
    
    for idx, event in enumerate(life_events):
        norm = normalize_aspect_code(str(_get_attr(event, "aspect", "")))
        if not norm:
            continue

        start = parse_iso_date(str(_get_attr(event, "startDate", "")))
        end = parse_iso_date(str(_get_attr(event, "endDate", "")))
        exact = parse_iso_date(str(_get_attr(event, "exactDate", "")))

        active_start = max(start, start_date)
        active_end = min(end, end_date)
        if active_start > active_end:
            continue

        direct, reverse = symmetric_keys(norm)
        implication = rule_maps.transit_daily_implications.get(direct) or rule_maps.transit_daily_implications.get(reverse)
        mapped = implication is not None

        if not implication:
            nature = str(_get_attr(event, "aspectNature", "Neutral")).lower()
            desc = str(_get_attr(event, "description", "")).strip()
            implication = f"General {nature} purchasing climate {desc}".strip()

        asp_type = _aspect_type(direct)
        ev_type = str(_get_attr(event, "eventType", "MINOR")).upper()
        weight = _event_weight(ev_type, cfg)
        amplitude = _amplitude(ev_type, cfg)
        polarity = _polarity(str(_get_attr(event, "aspectNature", "Negative")))

        asp_weight = cfg.aspect_type_weights.get(asp_type, 0.8)

        rows.append({
            "event_index": idx,
            "polarity": polarity,
            "base_amplitude": amplitude,
            "aspect_weight": asp_weight,
            "event_weight": weight,
            "start_index": (active_start - start_date).days,
            "end_index": (active_end - start_date).days,
            "exact_index": (exact - start_date).days,
            "span_length": (end - start).days + 1,
            "aspect_key": direct,
            "implication": implication,
            "is_mapped": mapped,
            "is_major": ev_type == "MAJOR",
            "is_moon": direct.startswith("MOO "),
            "is_hard_aspect": asp_type in HARD_ASPECTS,
            "has_outer_planet": _has_outer_planet_hard_aspect(direct),
        })
    
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _compute_daily_contributions_vectorized(
    events_df: pd.DataFrame,
    n_days: int,
    purchase_type: str,
    cfg: ShoppingCfg,
) -> Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized computation of daily score contributions.
    
    Returns:
        - daily_deltas: array of shape (n_days,) with score contributions
        - daily_stats: dict with mapped_count, major_count, etc.
        - contribution_matrix: array of shape (n_events, n_days)
        - implication_values: array of implication strings aligned to events
        - aspect_values: array of aspect strings aligned to events
    """
    if events_df.empty:
        empty_stats = {
            "mapped_count": np.zeros(n_days, dtype=int),
            "major_count": np.zeros(n_days, dtype=int),
            "positive_abs": np.zeros(n_days),
            "negative_abs": np.zeros(n_days),
        }
        return np.zeros(n_days), empty_stats, np.zeros((0, n_days)), np.array([]), np.array([])
    
    # Get purchase-type modifiers
    base_amp = BASE_AMPLITUDE.get(purchase_type, 1.0)
    risk_mult = RISK_MULTIPLIER.get(purchase_type, 1.0)
    
    starts = events_df["start_index"].to_numpy(dtype=int)[:, None]
    ends = events_df["end_index"].to_numpy(dtype=int)[:, None]
    exacts = events_df["exact_index"].to_numpy(dtype=int)[:, None]
    spans = np.maximum(events_df["span_length"].to_numpy(dtype=float)[:, None], 1.0)
    days = np.arange(n_days)[None, :]

    active_mask = (days >= starts) & (days <= ends)
    distance = np.abs(days - exacts)
    proximity = np.clip(1.0 - np.minimum(distance / spans, 1.0), 0.0, 1.0) * active_mask

    polarity = events_df["polarity"].to_numpy(dtype=float)
    amplitude = events_df["base_amplitude"].to_numpy(dtype=float)
    asp_weight = events_df["aspect_weight"].to_numpy(dtype=float)
    ev_weight = events_df["event_weight"].to_numpy(dtype=float)
    is_hard = events_df["is_hard_aspect"].to_numpy(dtype=bool)
    has_outer = events_df["has_outer_planet"].to_numpy(dtype=bool)

    effective_amplitude = amplitude.copy()
    positive_mask = polarity > 0
    hard_negative_mask = (~positive_mask) & is_hard
    effective_amplitude[positive_mask] *= base_amp
    effective_amplitude[hard_negative_mask] *= risk_mult

    if purchase_type == "luxury":
        luxury_outer_mask = hard_negative_mask & has_outer
        effective_amplitude[luxury_outer_mask] *= 1.2

    event_base = (polarity * ev_weight * asp_weight * effective_amplitude)[:, None]
    contribution_matrix = event_base * proximity

    daily_deltas = contribution_matrix.sum(axis=0)
    daily_positive = np.clip(contribution_matrix, 0.0, None).sum(axis=0)
    daily_negative = np.clip(-contribution_matrix, 0.0, None).sum(axis=0)

    is_mapped = events_df["is_mapped"].to_numpy(dtype=bool)[:, None]
    is_major = events_df["is_major"].to_numpy(dtype=bool)[:, None]
    daily_mapped = (is_mapped & active_mask).sum(axis=0)
    daily_major = (is_major & active_mask).sum(axis=0)

    stats = {
        "mapped_count": daily_mapped,
        "major_count": daily_major,
        "positive_abs": daily_positive,
        "negative_abs": daily_negative,
    }

    implication_values = events_df["implication"].to_numpy(dtype=str)
    aspect_values = events_df["aspect_key"].to_numpy(dtype=str)

    return daily_deltas, stats, contribution_matrix, implication_values, aspect_values


@overload
def score_daily_shopping(
    life_events: List[Any],
    start_date: date,
    n_days: int,
    profile: SpendProfile,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
    return_metrics: Literal[False] = False,
) -> List[DailyScore]: ...


@overload
def score_daily_shopping(
    life_events: List[Any],
    start_date: date,
    n_days: int,
    profile: SpendProfile,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
    return_metrics: Literal[True],
) -> Tuple[List[DailyScore], Dict[str, Any]]: ...


def score_daily_shopping(
    life_events: List[Any],
    start_date: date,
    n_days: int,
    profile: SpendProfile,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
    return_metrics: bool = False,
) -> List[DailyScore] | Tuple[List[DailyScore], Dict[str, Any]]:
    """Score daily shopping climate with purchase_type awareness.
    
    Returns:
        Tuple of (daily_scores, metrics_data)
    """
    if n_days <= 0:
        return ([], {}) if return_metrics else []
    
    # Check and warn if n_days too large
    if n_days > 180:
        import warnings
        warnings.warn(
            f"n_days={n_days} exceeds recommended limit of 180. "
            "Consider using weekly aggregation mode for better performance.",
            UserWarning,
        )

    end_date = start_date + timedelta(days=n_days - 1)
    purchase_type = cfg.purchase_type

    # Preprocess events into structured DataFrame for vectorization
    events_df = _preprocess_events(life_events, start_date, end_date, rule_maps, cfg)
    
    # Compute daily contributions using vectorized operations
    daily_deltas, stats, contribution_matrix, implication_values, aspect_values = _compute_daily_contributions_vectorized(
        events_df, n_days, purchase_type, cfg
    )
    daily_drivers: List[List[Driver]] = [[] for _ in range(n_days)]

    if contribution_matrix.size > 0:
        topk = max(1, cfg.top_driver_limit)
        for day_idx in range(n_days):
            day_contrib = contribution_matrix[:, day_idx]
            nonzero_idx = np.flatnonzero(day_contrib)
            if nonzero_idx.size == 0:
                continue

            if nonzero_idx.size > topk:
                candidate = nonzero_idx[np.argpartition(np.abs(day_contrib[nonzero_idx]), -topk)[-topk:]]
            else:
                candidate = nonzero_idx

            ordered = candidate[np.argsort(np.abs(day_contrib[candidate]))[::-1]]
            for event_idx in ordered:
                daily_drivers[day_idx].append(
                    Driver(
                        code="TRANSIT_EVENT",
                        weight=float(day_contrib[event_idx]),
                        implication=str(implication_values[event_idx]),
                        matched_aspect=str(aspect_values[event_idx]),
                    )
                )
    
    mapped_count = stats.get("mapped_count", np.zeros(n_days))
    major_count = stats.get("major_count", np.zeros(n_days))
    positive_abs = stats.get("positive_abs", np.zeros(n_days))
    negative_abs = stats.get("negative_abs", np.zeros(n_days))

    # Add moon triggers if enabled
    if cfg.moon_trigger_enabled:
        _add_moon_triggers(
            start_date,
            end_date,
            events_df,
            rule_maps,
            cfg,
            daily_deltas,
            daily_drivers,
            mapped_count,
        )

    # Add moon phases if configured
    if cfg.moon_trigger_enabled and cfg.moon_phase_by_date:
        _add_moon_phases(
            start_date,
            end_date,
            cfg,
            rule_maps,
            daily_deltas,
            daily_drivers,
            mapped_count,
        )

    # Build final daily scores
    results: List[DailyScore] = []
    
    for day_idx, day in enumerate(daterange_inclusive(start_date, end_date)):
        raw = cfg.daily_base_score + daily_deltas[day_idx]
        
        # Apply spend profile adjustments based on purchase_type
        if profile.category == "Impulsive/High-Spend Risk" and purchase_type == "luxury":
            # Behavioral guardrail: reduce score by 5-10 points
            adjustment = -7.5
            raw += adjustment
            daily_drivers[day_idx].append(
                Driver(
                    code="PROFILE_GUARDRAIL",
                    weight=adjustment,
                    implication="Impulsive profile + luxury purchase: extra caution applied",
                    matched_aspect=None,
                )
            )
        
        if profile.category == "Ultra Thrifty" and purchase_type == "essentials":
            # Boost neutral baseline for essentials
            adjustment = 3.0
            raw += adjustment
            daily_drivers[day_idx].append(
                Driver(
                    code="PROFILE_BOOST",
                    weight=adjustment,
                    implication="Thrifty profile + essentials: baseline raised",
                    matched_aspect=None,
                )
            )
        
        score = to_int_score(raw, 0, 100)
        
        # Compute confidence
        mc = int(mapped_count[day_idx]) if day_idx < len(mapped_count) else 0
        mjc = int(major_count[day_idx]) if day_idx < len(major_count) else 0
        pos_abs = positive_abs[day_idx] if day_idx < len(positive_abs) else 0.0
        neg_abs = negative_abs[day_idx] if day_idx < len(negative_abs) else 0.0
        
        conflict_penalty = 0.0
        if pos_abs > 4.0 and neg_abs > 4.0:
            conflict_penalty = min(pos_abs, neg_abs) * 0.01

        confidence = 0.7 + mc * 0.03 + mjc * 0.05 - conflict_penalty
        confidence = round(clamp(confidence, 0.0, 1.0), 3)

        top = sorted(daily_drivers[day_idx], key=lambda d: abs(d.weight), reverse=True)[: cfg.top_driver_limit]
        note = _build_note(score=score, strongest=top[0] if top else None, profile=profile, purchase_type=purchase_type)

        results.append(
            DailyScore(
                date=day,
                score=score,
                confidence=confidence,
                top_drivers=top,
                note=note,
            )
        )

    # Collect metrics data for caller
    total_events = len(life_events)
    mapped_events = int(events_df["is_mapped"].sum()) if not events_df.empty else 0
    fallback_events = total_events - mapped_events if not events_df.empty else total_events
    
    metrics_data = {
        "total_events": total_events,
        "mapped_events": mapped_events,
        "fallback_events": fallback_events,
        "life_events": life_events,  # Pass through for metrics computation
    }

    if return_metrics:
        return results, metrics_data
    return results


def _add_moon_triggers(
    start_date: date,
    end_date: date,
    events_df: pd.DataFrame,
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
    daily_deltas: np.ndarray,
    daily_drivers: List[List[Driver]],
    mapped_count: np.ndarray,
) -> None:
    """Add moon trigger contributions (modifies arrays in-place)."""
    if events_df.empty:
        return
    
    moon_events = events_df[events_df["is_moon"]]
    
    for _, event in moon_events.iterrows():
        start_idx = int(event["start_index"])
        end_idx = int(event["end_index"])
        exact_idx = int(event["exact_index"])
        span_len = int(event["span_length"])
        polarity = event["polarity"]
        aspect_key = event["aspect_key"]
        
        direct, reverse = symmetric_keys(aspect_key)
        moon_imp = rule_maps.moon_spending_implications.get(direct) or rule_maps.moon_spending_implications.get(reverse)
        moon_imp = moon_imp or "Moon spending trigger"
        
        for day_idx in range(start_idx, end_idx + 1):
            if 0 <= day_idx < len(daily_deltas):
                prox = _numeric_proximity(day_idx, exact_idx, span_len)
                moon_bonus = polarity * cfg.moon_trigger_amplitude * prox
                daily_deltas[day_idx] += moon_bonus
                daily_drivers[day_idx].append(
                    Driver(code="MOON_TRIGGER", weight=moon_bonus, implication=moon_imp, matched_aspect=aspect_key)
                )


def _add_moon_phases(
    start_date: date,
    end_date: date,
    cfg: ShoppingCfg,
    rule_maps: RuleMaps,
    daily_deltas: np.ndarray,
    daily_drivers: List[List[Driver]],
    mapped_count: np.ndarray,
) -> None:
    """Add moon phase contributions (modifies arrays in-place)."""
    if not cfg.moon_phase_by_date:
        return

    for key_date, phase in cfg.moon_phase_by_date.items():
        day = parse_iso_date(key_date)
        if day < start_date or day > end_date:
            continue
        
        day_idx = (day - start_date).days
        if day_idx < 0 or day_idx >= len(daily_deltas):
            continue
        
        phase_key = f"MOO PHASE {str(phase).upper()}"
        implication = rule_maps.transit_daily_implications.get(phase_key)
        if not implication:
            continue
        
        phase_weight = cfg.moon_trigger_amplitude * 0.8
        daily_deltas[day_idx] += phase_weight
        daily_drivers[day_idx].append(
            Driver(code="MOON_PHASE", weight=phase_weight, implication=implication, matched_aspect=phase_key)
        )
        mapped_count[day_idx] += 1
