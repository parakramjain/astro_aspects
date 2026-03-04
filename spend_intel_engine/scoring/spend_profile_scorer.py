from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from spend_intel_engine.domain.enums import SpendCategory
from spend_intel_engine.domain.models import Driver, NatalStructureSignals, RuleMaps, ShoppingCfg, SpendProfile
from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code, symmetric_keys
from spend_intel_engine.utils.cache import cached_natal_structure_features
from spend_intel_engine.utils.numbers import clamp, to_int_score

SIGN_RULER = {
    "ARIES": "MAR",
    "TAURUS": "VEN",
    "GEMINI": "MER",
    "CANCER": "MOO",
    "LEO": "SUN",
    "VIRGO": "MER",
    "LIBRA": "VEN",
    "SCORPIO": "PLU",
    "SAGITTARIUS": "JUP",
    "CAPRICORN": "SAT",
    "AQUARIUS": "SAT",
    "PISCES": "JUP",
}

VENUS_DIGNITY = {
    "TAURUS": 0.9,
    "LIBRA": 0.9,
    "PISCES": 0.75,
    "VIRGO": 0.25,
    "SCORPIO": 0.35,
    "ARIES": 0.45,
}

THRIFT_PAIRS = {
    frozenset(("VEN", "SAT")),
    frozenset(("JUP", "SAT")),
    frozenset(("MER", "SAT")),
}

SPEND_PAIRS = {
    frozenset(("VEN", "JUP")),
    frozenset(("VEN", "NEP")),
    frozenset(("VEN", "URA")),
    frozenset(("VEN", "PLU")),
    frozenset(("MOO", "VEN")),
    frozenset(("MAR", "JUP")),
}

SUPPORTIVE = {"CON", "TRI", "SEX"}
HARD = {"SQR", "OPP"}

CATEGORY_DESCRIPTIONS = {
    SpendCategory.ULTRA_THRIFTY.value: "Strong control and delayed-gratification tendencies dominate spending decisions.",
    SpendCategory.THRIFTY.value: "Practicality and value checks are usually prioritized over impulse purchases.",
    SpendCategory.BALANCED.value: "Spending tendencies are mixed, with both caution and enjoyment in moderation.",
    SpendCategory.SPENDER.value: "You lean toward comfort and lifestyle spending unless clear limits are set.",
    SpendCategory.IMPULSIVE.value: "High-stimulation buying patterns are active; strict guardrails reduce overspend risk.",
}


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    return getattr(obj, key, default)


def _planet_map(natal_chart_data: Any) -> Dict[str, Any]:
    planets = _get_attr(natal_chart_data, "planets", []) or []
    mapped: Dict[str, Any] = {}
    for p in planets:
        name = str(_get_attr(p, "planetName", "")).upper()
        mapped[name[:3]] = p
    return mapped


def _build_aspect_count(natal_aspects: List[Any]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for item in natal_aspects:
        normalized = normalize_aspect_code(_get_attr(item, "aspect", ""))
        if not normalized:
            continue
        left, _, right = normalized.split()
        counter[left] += 1
        counter[right] += 1
    return dict(counter)


def _angular_bonus(house_number: Optional[int]) -> float:
    if house_number in {1, 4, 7, 10}:
        return 0.3
    if house_number in {2, 8, 11}:
        return 0.15
    return 0.0


def _venus_condition_score(planet_map: Dict[str, Any]) -> float:
    venus = planet_map.get("VEN")
    if not venus:
        return 0.5
    sign = str(_get_attr(venus, "planetSign", "")).upper()
    house_num = int(_get_attr(venus, "houseNumber", 0) or 0)
    dignity = VENUS_DIGNITY.get(sign, 0.55)
    return clamp(dignity + _angular_bonus(house_num), 0.0, 1.0)


def _prominence_score(planet: Any, asc_aspects_count: int = 0) -> float:
    if not planet:
        return 0.4
    house_num = int(_get_attr(planet, "houseNumber", 0) or 0)
    base = 0.45 + _angular_bonus(house_num)
    if asc_aspects_count > 0:
        base += 0.1
    return clamp(base, 0.0, 1.0)


def _house_sign_by_number(planet_map: Dict[str, Any], target_house: int) -> Optional[str]:
    for planet in planet_map.values():
        if int(_get_attr(planet, "houseNumber", 0) or 0) == target_house:
            sign = str(_get_attr(planet, "houseSign", "")).upper()
            if sign:
                return sign
    return None


def _chart_hash_from_planets(planet_map: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in sorted(planet_map.keys()):
        planet = planet_map[key]
        parts.append(
            f"{key}:{_get_attr(planet, 'planetSign', '')}:{_get_attr(planet, 'houseNumber', '')}:{_get_attr(planet, 'houseSign', '')}"
        )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _ruler_stability_score(
    house_sign: Optional[str],
    planet_map: Dict[str, Any],
    aspect_counts: Dict[str, int],
) -> float:
    if not house_sign:
        return 0.5
    ruler = SIGN_RULER.get(house_sign)
    if not ruler:
        return 0.5
    planet = planet_map.get(ruler)
    if not planet:
        return 0.5
    house_num = int(_get_attr(planet, "houseNumber", 0) or 0)
    aspect_count = aspect_counts.get(ruler, 0)
    return clamp(0.45 + _angular_bonus(house_num) + min(0.2, aspect_count * 0.03), 0.0, 1.0)


def _compute_structure_signals(natal_chart_data: Any, natal_aspects: List[Any], rule_maps: RuleMaps) -> NatalStructureSignals:
    planet_map = _planet_map(natal_chart_data)
    aspect_counts = _build_aspect_count(natal_aspects)

    saturn = planet_map.get("SAT")
    jupiter = planet_map.get("JUP")

    second_sign = _house_sign_by_number(planet_map, 2)
    eighth_sign = _house_sign_by_number(planet_map, 8)

    values = {
        "VENUS_CONDITION": _venus_condition_score(planet_map),
        "SATURN_PROMINENCE": _prominence_score(saturn),
        "JUPITER_PROMINENCE": _prominence_score(jupiter),
        "SECOND_RULER_STABILITY": _ruler_stability_score(second_sign, planet_map, aspect_counts),
        "EIGHTH_RULER_PRESSURE": _ruler_stability_score(eighth_sign, planet_map, aspect_counts),
    }

    chart_hash = _chart_hash_from_planets(planet_map)
    serialized = json.dumps(values, sort_keys=True)
    cached_values = cached_natal_structure_features(chart_hash, rule_maps.ruleset_version, serialized)

    return NatalStructureSignals(values=cached_values, implications=rule_maps.natal_structure_implications)


def _category_from_score(score: int) -> str:
    if score <= 20:
        return SpendCategory.ULTRA_THRIFTY.value
    if score <= 40:
        return SpendCategory.THRIFTY.value
    if score <= 60:
        return SpendCategory.BALANCED.value
    if score <= 80:
        return SpendCategory.SPENDER.value
    return SpendCategory.IMPULSIVE.value


def score_spend_profile(
    natal_chart_data: Any,
    natal_aspects: List[Any],
    rule_maps: RuleMaps,
    cfg: ShoppingCfg,
) -> SpendProfile:
    thrift_score = 0.0
    spend_score = 0.0
    drivers: List[Driver] = []

    implied_aspects = {**rule_maps.natal_spend_implications, **rule_maps.moon_spending_implications}

    for item in natal_aspects:
        normalized = normalize_aspect_code(_get_attr(item, "aspect", ""))
        if not normalized:
            continue

        direct, reverse = symmetric_keys(normalized)
        implication = implied_aspects.get(direct) or implied_aspects.get(reverse)
        if not implication:
            continue

        left, aspect_type, right = direct.split()
        pair = frozenset((left, right))
        strength = float(_get_attr(item, "strength", 0.0) or 0.0)
        base_weight = cfg.aspect_type_weights.get(aspect_type, 0.75) * strength

        signed = base_weight if aspect_type in SUPPORTIVE else -base_weight

        if pair in THRIFT_PAIRS:
            thrift_score += signed
            drivers.append(Driver(code="NATAL_THRIFT", weight=signed, implication=implication, matched_aspect=direct))
        elif pair in SPEND_PAIRS:
            spend_score += signed
            drivers.append(Driver(code="NATAL_SPEND", weight=signed, implication=implication, matched_aspect=direct))
        else:
            spend_score += signed * 0.4
            thrift_score += -signed * 0.2
            drivers.append(Driver(code="NATAL_MIXED", weight=signed * 0.4, implication=implication, matched_aspect=direct))

    structure = _compute_structure_signals(natal_chart_data, natal_aspects, rule_maps)

    for signal_code, signal_value in structure.values.items():
        signal_imp = structure.implications.get(signal_code, "Structural tendency from natal chart")
        signal_w = cfg.structure_feature_weights.get(signal_code, 1.0) * (signal_value - 0.5)

        if signal_code in {"SATURN_PROMINENCE", "SECOND_RULER_STABILITY"}:
            thrift_score += signal_w
        elif signal_code in {"JUPITER_PROMINENCE", "EIGHTH_RULER_PRESSURE"}:
            spend_score += signal_w
        else:
            spend_score += signal_w * 0.7
            thrift_score += signal_w * 0.3

        drivers.append(Driver(code=signal_code, weight=signal_w, implication=signal_imp, matched_aspect=None))

    raw_score = cfg.base_score + (spend_score - thrift_score) * cfg.spend_scale
    score = to_int_score(raw_score, 0, 100)
    category = _category_from_score(score)

    top_drivers = sorted(drivers, key=lambda d: abs(d.weight), reverse=True)[: cfg.top_driver_limit]
    phrases = [d.implication for d in top_drivers[: cfg.profile_driver_phrase_limit]]
    suffix = " ".join(phrases)
    description = CATEGORY_DESCRIPTIONS[category]
    if suffix:
        description = f"{description} Key drivers: {suffix}"[:280]

    return SpendProfile(
        score=score,
        category=category,
        description=description,
        top_drivers=top_drivers,
    )
