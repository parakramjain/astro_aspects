"""synastry_group_services
================================================================================
Group synastry and compatibility analysis for multiple people (friends, teams,
families). Computes pairwise KPIs, aggregates to group KPIs, and produces a
shareable card payload.

Assumed external modules (guarded imports; TODO for full integration):
- astro_core.astro_core: calc_planet_pos(person-like) / get_house_cusps(person-like)
- services.synastry_services: calculate_synastry (pairwise KPI engine 0..10)
- services.sunastry_vedic_services: gun_milan_score OR compute_ashtakoota_score

Python: 3.11+
Pydantic: v2

Public API
----------
- analyze_group(inputs, compatibility_type) -> GroupResult
- compute_pair(personA, personB, compatibility_type) -> PairwiseResult
- kpi_catalog() -> list[str]
- weights_profile(compatibility_type) -> dict[str,float]
- to_shareable_card(result: GroupResult) -> dict
- explain_pair_kpis(pair: PairwiseResult) -> dict[str,str]
- analyze_group_api_payload(people, compatibility_type) -> dict for API layer

Data contract (Pydantic v2 models)
----------------------------------
- PersonInput
- PairwiseResult
- GroupKPI
- GroupResult
- GroupSettings

Doctests
--------
>>> scale_0_100(5, 0, 10)
50.0
>>> clamp_0_100(123.4)
100.0
>>> clamp_0_100(-7)
0.0
>>> 'Friendship Group' in weights_profile('Friendship Group')['__type']
True

Notes
-----
- This module is designed to be resilient in environments where some assumed
  modules are not available. In such cases, computations degrade gracefully
  with warnings and neutral scores.
- Replace TODO-labeled stubs with project-specific logic as those modules are
  integrated.
"""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from itertools import combinations
from math import isnan
import json
import logging
import os
from statistics import mean, pstdev
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple
import sys

try:  # Optional numpy for simple stats; guard import
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - optional
    _np = None  # type: ignore

try:  # Optional networkx for cohesion metrics
    import networkx as _nx  # type: ignore
except Exception:  # pragma: no cover - optional
    _nx = None  # type: ignore

def _ensure_project_root_on_syspath() -> None:
    """Ensure project root (parent of this file's directory) is in sys.path.

    This helps when running modules directly or from atypical working dirs
    so that local packages like 'astro_core' and 'schemas' resolve correctly.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if root not in sys.path:
        sys.path.insert(0, root)


# Initialize logging early (needed by import fallbacks)
_LOG_LEVEL = os.environ.get("GROUP_SYN_LOG", "info").lower()
_LEVEL_MAP = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARN, "warning": logging.WARN}
logger = logging.getLogger("synastry_group_services")
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
logger.setLevel(_LEVEL_MAP.get(_LOG_LEVEL, logging.INFO))

# Try project astro core with fallback to add project root and retry
try:
    import astro_core.astro_core as _ac_mod  # type: ignore
    ac_calc_planet_pos = getattr(_ac_mod, "calc_planet_pos", None)
    ac_get_house_cusps = getattr(_ac_mod, "get_house_cusps", None)
    logger.debug("Imported astro_core.astro_core successfully.")
except Exception:  # pragma: no cover - optional
    _ensure_project_root_on_syspath()
    try:
        if "astro_core" in sys.modules:
            del sys.modules["astro_core"]
        import astro_core.astro_core as _ac_mod  # type: ignore
        ac_calc_planet_pos = getattr(_ac_mod, "calc_planet_pos", None)
        ac_get_house_cusps = getattr(_ac_mod, "get_house_cusps", None)
        logger.debug("Imported astro_core.astro_core after sys.path fix.")
    except Exception:
        ac_calc_planet_pos = None  # type: ignore
        ac_get_house_cusps = None  # type: ignore
        logger.warning("Failed to import astro_core.astro_core; natal computations will be neutral.")

# Reuse project synastry services instead of a hypothetical synastry_core
try:
    from services.synastry_services import calculate_synastry as sg_calculate_synastry  # type: ignore
    logger.debug("Imported services.synastry_services.calculate_synastry.")
except Exception:  # pragma: no cover - optional
    _ensure_project_root_on_syspath()
    try:
        if "services.synastry_services" in sys.modules:
            del sys.modules["services.synastry_services"]
        from services.synastry_services import calculate_synastry as sg_calculate_synastry  # type: ignore
        logger.debug("Imported services.synastry_services.calculate_synastry after sys.path fix.")
    except Exception:
        sg_calculate_synastry = None  # type: ignore
        logger.warning("Failed to import services.synastry_services.calculate_synastry; using neutral KPIs.")

# Vedic services (this repo has services/synastry_vedic_services.py)
try:
    from services.synastry_vedic_services import compute_ashtakoota_score as vedic_compute_ashtakoota  # type: ignore
except Exception:  # pragma: no cover - optional
    vedic_compute_ashtakoota = None  # type: ignore

from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError
from pydantic import ConfigDict

# Import shared schemas
# Import shared schemas with a robust fallback to local file when executed as a script.
try:
    from schemas import (
        BirthPayload,
        GroupSettings as SchemaGroupSettings,
        PairwiseResult as SchemaPairwiseResult,
        GroupKPI as SchemaGroupKPI,
        GroupResult as SchemaGroupResult,
    )
except Exception:
    # When running this file directly (python services/synastry_group_services.py),
    # importing "schemas" may resolve to a third-party package instead of the local
    # project file. Insert project root into sys.path and retry.
    import sys as _sys
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _ROOT not in _sys.path:
        _sys.path.insert(0, _ROOT)
    if "schemas" in _sys.modules:
        del _sys.modules["schemas"]
    from schemas import (
        BirthPayload,
        GroupSettings as SchemaGroupSettings,
        PairwiseResult as SchemaPairwiseResult,
        GroupKPI as SchemaGroupKPI,
        GroupResult as SchemaGroupResult,
    )


# --------------------------------- Logging ---------------------------------
_LOG_LEVEL = os.environ.get("GROUP_SYN_LOG", "info").lower()
_LEVEL_MAP = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARN, "warning": logging.WARN}
logger = logging.getLogger("synastry_group_services")
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
logger.setLevel(_LEVEL_MAP.get(_LOG_LEVEL, logging.INFO))


# ----------------------------- Constants & Defaults -----------------------------
CompatibilityType = Literal["Friendship Group", "Professional Team", "Sport Team", "Family", "Relative"]
COMPATIBILITY_TYPES: List[CompatibilityType] = [
    "Friendship Group",
    "Professional Team",
    "Sport Team",
    "Family",
    "Relative",
]

def is_supported_type(t: str) -> bool:
    """Return True if t is a supported compatibility type label."""
    return t in COMPATIBILITY_TYPES

DEFAULT_KPIS: List[str] = [
    "Emotional Harmony",
    "Communication Flow",
    "Trust & Stability",
    "Leadership & Drive",
    "Conflict Potential",  # inverse KPI; lower conflict -> higher score
    "Creativity & Vision",
    "Work Ethic & Discipline",
    "Decision Alignment",
    "Risk Tolerance Fit",
    "Values Alignment",
]

DEFAULT_ASPECT_WEIGHTS: Dict[str, float] = {
    "conjunction": 1.0,
    "trine": 0.9,
    "sextile": 0.7,
    "square": -0.7,
    "opposition": -0.8,
    "quincunx": -0.4,
}

# Orbs: generic defaults and selective planet tweaks (deg)
DEFAULT_ORBS: Dict[str, Any] = {
    "conjunction": {"base": 8.0, "Moon": 6.0, "Mercury": 5.0, "Venus": 5.0, "Sun": 9.0, "Saturn": 8.5, "Jupiter": 8.5},
    "trine": {"base": 7.0, "Moon": 5.5, "Mercury": 5.0, "Venus": 5.0, "Sun": 8.0, "Saturn": 7.5, "Jupiter": 7.5},
    "sextile": {"base": 5.5, "Moon": 4.5, "Mercury": 4.0, "Venus": 4.0, "Sun": 6.0, "Saturn": 5.5, "Jupiter": 5.5},
    "square": {"base": 6.0, "Moon": 5.0, "Mercury": 4.5, "Venus": 4.5, "Sun": 7.0, "Saturn": 6.5, "Jupiter": 6.5},
    "opposition": {"base": 6.5, "Moon": 5.5, "Mercury": 5.0, "Venus": 5.0, "Sun": 7.5, "Saturn": 7.0, "Jupiter": 7.0},
    "quincunx": {"base": 3.5, "Moon": 3.0, "Mercury": 3.0, "Venus": 3.0, "Sun": 4.0, "Saturn": 3.5, "Jupiter": 3.5},
}

PLANET_WEIGHTS: Dict[str, float] = {
    "Sun": 1.0,
    "Moon": 1.1,
    "Mercury": 0.9,
    "Venus": 1.0,
    "Mars": 0.95,
    "Jupiter": 0.8,
    "Saturn": 0.9,
    "Uranus": 0.6,
    "Neptune": 0.6,
    "Pluto": 0.6,
}

SCORE_BANDS: List[Tuple[float, str, str]] = [
    (80.0, "Excellent Cohesion", "#16a34a"),
    (65.0, "Strong Team", "#22c55e"),
    (50.0, "Good", "#84cc16"),
    (35.0, "Mixed", "#f59e0b"),
    (0.0, "Challenging", "#ef4444"),
]


def _normalize_weights(d: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, float(v)) for v in d.values())
    if s <= 0:
        return {k: 0.0 for k in d}
    return {k: float(v) / s for k, v in d.items()}


TYPE_KPI_WEIGHTS: Dict[CompatibilityType, Dict[str, float]] = {
    "Friendship Group": _normalize_weights({
        "Emotional Harmony": 1.0,
        "Communication Flow": 1.0,
        "Trust & Stability": 1.0,
        "Leadership & Drive": 0.5,
        "Conflict Potential": 1.0,
        "Creativity & Vision": 0.8,
        "Work Ethic & Discipline": 0.5,
        "Decision Alignment": 0.7,
        "Risk Tolerance Fit": 0.6,
        "Values Alignment": 1.0,
    }),
    "Professional Team": _normalize_weights({
        "Emotional Harmony": 0.7,
        "Communication Flow": 1.0,
        "Trust & Stability": 1.0,
        "Leadership & Drive": 1.0,
        "Conflict Potential": 1.0,
        "Creativity & Vision": 0.9,
        "Work Ethic & Discipline": 1.0,
        "Decision Alignment": 1.0,
        "Risk Tolerance Fit": 0.8,
        "Values Alignment": 0.7,
    }),
    "Sport Team": _normalize_weights({
        "Emotional Harmony": 0.6,
        "Communication Flow": 0.9,
        "Trust & Stability": 0.8,
        "Leadership & Drive": 1.2,
        "Conflict Potential": 1.0,
        "Creativity & Vision": 0.7,
        "Work Ethic & Discipline": 1.0,
        "Decision Alignment": 0.9,
        "Risk Tolerance Fit": 1.0,
        "Values Alignment": 0.5,
    }),
    "Family": _normalize_weights({
        "Emotional Harmony": 1.2,
        "Communication Flow": 0.9,
        "Trust & Stability": 1.2,
        "Leadership & Drive": 0.5,
        "Conflict Potential": 1.0,
        "Creativity & Vision": 0.6,
        "Work Ethic & Discipline": 0.6,
        "Decision Alignment": 0.7,
        "Risk Tolerance Fit": 0.5,
        "Values Alignment": 1.0,
    }),
    "Relative": _normalize_weights({
        "Emotional Harmony": 0.9,
        "Communication Flow": 0.8,
        "Trust & Stability": 1.0,
        "Leadership & Drive": 0.4,
        "Conflict Potential": 1.0,
        "Creativity & Vision": 0.6,
        "Work Ethic & Discipline": 0.6,
        "Decision Alignment": 0.6,
        "Risk Tolerance Fit": 0.5,
        "Values Alignment": 1.0,
    }),
}


# -------------------------------- Data Models --------------------------------
class PersonInput(BirthPayload):  # extend shared BirthPayload
    """Alias that adds helpers on top of shared BirthPayload.

    We extend the shared BirthPayload with local helper methods without changing
    the serialized fields.
    """

    def validate_timezone(self) -> None:
        try:
            ZoneInfo(self.timeZone)  # field name per BirthPayload
        except Exception as e:  # pragma: no cover - environment dependent
            raise ValueError(f"Invalid IANA time zone: {self.timeZone}") from e

    def cache_key(self) -> str:
        return f"{self.name}|{self.dateOfBirth}|{self.timeOfBirth}|{float(self.latitude):.6f}|{float(self.longitude):.6f}"


PairwiseResult = SchemaPairwiseResult


GroupKPI = SchemaGroupKPI


GroupResult = SchemaGroupResult


# Use schema GroupSettings directly; instantiate with our defaults when missing
GroupSettings = SchemaGroupSettings


# ------------------------------- KPI Registry -------------------------------
_CUSTOM_KPI_RULES: Dict[str, Callable[[Any], float]] = {}


def register_custom_kpi(name: str, rule_fn: Callable[[Any], float]) -> None:
    """Register a custom KPI for extension.

    Args:
        name: KPI name
        rule_fn: Function receiving a context object and returning a score 0..100
    """
    if not name or not callable(rule_fn):
        raise ValueError("Invalid KPI registration: name and callable rule_fn required.")
    _CUSTOM_KPI_RULES[name] = rule_fn


# --------------------------------- Helpers ---------------------------------
def clamp_0_100(x: float) -> float:
    """Clamp a float to [0, 100].

    >>> clamp_0_100(101)
    100.0
    >>> clamp_0_100(-5)
    0.0
    """
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 100.0:
        return 100.0
    return v


def scale_0_100(x: float, min_x: float, max_x: float) -> float:
    """Scale x from [min_x, max_x] into [0, 100]. If degenerate, return 50.

    >>> scale_0_100(0, 0, 10)
    0.0
    >>> scale_0_100(5, 0, 10)
    50.0
    >>> scale_0_100(10, 0, 10)
    100.0
    """
    try:
        lo, hi, val = float(min_x), float(max_x), float(x)
    except Exception:
        return 50.0
    if hi == lo:
        return 50.0
    r = (val - lo) / (hi - lo)
    return clamp_0_100(r * 100.0)


def z_score_to_0_100(z: float) -> float:
    """Map a z-score to 0..100 via a sigmoid-like transform.

    We use 50 + 20*z clipped to ±2.5 sigma.
    """
    if z is None:
        return 50.0
    try:
        zf = float(z)
    except Exception:
        return 50.0
    zf = max(min(zf, 2.5), -2.5)
    return clamp_0_100(50.0 + 20.0 * zf)


def safe_mean(values: Iterable[float], default: float = 0.0) -> float:
    arr = [float(v) for v in values if v is not None and not isnan(float(v))]
    if not arr:
        return default
    return float(mean(arr))


def rank_top(d: Dict[str, float], n: int = 2, reverse: bool = True) -> List[Tuple[str, float]]:
    items = list(d.items())
    items.sort(key=lambda kv: kv[1], reverse=reverse)
    return items[:n]


def _badge_for_score(score: float) -> Tuple[str, str]:
    for threshold, label, color in SCORE_BANDS:
        if score >= threshold:
            return label, color
    return "Challenging", "#ef4444"


def describe_pair(kpis: Dict[str, float]) -> str:
    """Compose a concise description from KPI scores. <= 280 chars."""
    # Two strongest themes
    top2 = rank_top(kpis, 2, reverse=True)
    low1 = rank_top(kpis, 1, reverse=False)
    pos = ", ".join(f"{k}" for k, _ in top2)
    neg = ", ".join(f"{k}" for k, _ in low1)
    s = f"Strengths in {pos}. Watch {neg}."
    return s[:280]


# ------------------------------- Natal caching -------------------------------
def _person_to_natal_payload(p: PersonInput) -> Dict[str, Any]:
    # Convert PersonInput to the dict expected by astro core or synastry core if needed
    return {
        "name": p.name,
        "dateOfBirth": p.dateOfBirth,
        "timeOfBirth": p.timeOfBirth,
        "placeOfBirth": p.placeOfBirth,
        "timeZone": p.timeZone,
        "latitude": p.latitude,
        "longitude": p.longitude,
    }


@lru_cache(maxsize=256)
def get_natal(person_key: str, person_payload_json: str) -> Dict[str, Any]:
    """LRU-cached natal computation wrapper.

    Args:
        person_key: cache key (from PersonInput.cache_key)
        person_payload_json: serialized person dict for underlying calls
    Returns:
        Natal data dict (shape flexible, feeds synastry_core). If astro core is
        unavailable, returns an empty dict and logs a warning.
    """
    payload = json.loads(person_payload_json)
    if ac_calc_planet_pos is None:
        logger.warning("astro_core not available; returning empty natal for %s", payload.get("name"))
        return {"planets": {}, "houses": {}}

    try:
        # Prefer a unified call if project exposes a person-centric API (TODO)
        # Fallback: pass date/time/tz through calc_planet_pos if signature supports it (project-specific).
        planets = ac_calc_planet_pos(
            payload.get("dateOfBirth"), payload.get("timeOfBirth"), tz_str=payload.get("timeZone", "UTC")
        )
    except TypeError:
        # Different signature; try without tz
        planets = ac_calc_planet_pos(payload.get("dateOfBirth"), payload.get("timeOfBirth"))  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover - surfacing
        logger.warning("astro_core.calc_planet_pos failed for %s: %s", payload.get("name"), e)
        planets = {}

    houses = {}
    if ac_get_house_cusps is not None:
        try:
            houses = ac_get_house_cusps(payload)
        except Exception:  # pragma: no cover - optional
            houses = {}

    return {"planets": planets, "houses": houses, "person": payload}


# ---------------------------- Pairwise computation ----------------------------
def _pair_kpi_scores(
    natalA: Dict[str, Any],
    natalB: Dict[str, Any],
    *,
    compatibility_type: CompatibilityType,
    settings: Optional[GroupSettings] = None,
) -> Dict[str, float]:
    """Compute KPI scores for a pair given their natals.

    Reuses services.synastry_services.calculate_synastry (0..10 KPI scale) and maps
    those KPIs onto the broader group KPI set. Missing KPIs receive heuristic or
    neutral scores (50). If synastry services unavailable, returns neutral scores.
    """
    settings = settings or GroupSettings()

    # Neutral baseline
    kpi_scores: Dict[str, float] = {k: 50.0 for k in DEFAULT_KPIS}
    print("Next step is to calculate synastry KPIs...")
    if sg_calculate_synastry is not None:
        try:
            p1 = natalA.get("person", {})
            p2 = natalB.get("person", {})
            print("Calculating synastry for:", p1.get("name"), "and", p2.get("name"))
            syn = sg_calculate_synastry(p1, p2)  # returns 0..10 KPIs
            base = syn.get("kpi_scores", {})  # emotional, communication, chemistry, stability, elemental_balance
            print("  Synastry KPIs:", base)

            # Map 0..10 -> 0..100 and rename
            def _scale10(v: float | int | None) -> float:
                if v is None:
                    return 50.0
                try:
                    fv = float(v)
                except Exception:
                    return 50.0
                return clamp_0_100(fv * 10.0)

            emotional = _scale10(base.get("emotional"))
            communication = _scale10(base.get("communication"))
            chemistry = _scale10(base.get("chemistry"))
            stability = _scale10(base.get("stability"))
            elemental = _scale10(base.get("elemental_balance"))

            # Direct mappings
            kpi_scores["Emotional Harmony"] = emotional
            kpi_scores["Communication Flow"] = communication
            kpi_scores["Trust & Stability"] = stability
            kpi_scores["Creativity & Vision"] = chemistry  # heuristic
            kpi_scores["Values Alignment"] = elemental

            # Heuristic derivations for KPIs not directly covered
            kpi_scores["Conflict Potential"] = clamp_0_100((emotional + communication) / 2.0)
            kpi_scores["Leadership & Drive"] = clamp_0_100((chemistry + stability) / 2.0)
            kpi_scores["Work Ethic & Discipline"] = stability
            kpi_scores["Decision Alignment"] = clamp_0_100((communication + stability) / 2.0)
            kpi_scores["Risk Tolerance Fit"] = elemental  # placeholder mapping

        except Exception as e:  # pragma: no cover - degrade gracefully
            logger.warning("synastry_services failure: %s", e)

    # Optional Vedic Harmony (extra KPI if desired) - keep neutral if failure
    try:
        if vedic_compute_ashtakoota is not None:
            p1 = natalA.get("person", {})
            p2 = natalB.get("person", {})
            res = vedic_compute_ashtakoota(p1, p2)  # type: ignore[call-arg]
            total_36 = float(res.get("total", 0.0))
            vedic_score = clamp_0_100((total_36 / 36.0) * 100.0)
            # Do not append to DEFAULT_KPIS globally; if needed could expose separately.
            kpi_scores.setdefault("Vedic Harmony", vedic_score)
    except Exception as e:  # pragma: no cover - optional
        logger.debug("Vedic score not available: %s", e)

    return {k: float(kpi_scores.get(k, 50.0)) for k in DEFAULT_KPIS}


def _pair_total_score(kpi_scores: Dict[str, float], *, compatibility_type: CompatibilityType) -> float:
    weights = TYPE_KPI_WEIGHTS.get(compatibility_type, {})
    if not weights:
        weights = _normalize_weights({k: 1.0 for k in DEFAULT_KPIS})
    total = 0.0
    for k, w in weights.items():
        v = float(kpi_scores.get(k, 50.0))
        total += w * v
    return clamp_0_100(total)


def compute_pair(
    personA: PersonInput,
    personB: PersonInput,
    compatibility_type: CompatibilityType,
    *,
    settings: Optional[GroupSettings] = None,
) -> PairwiseResult:
    """Compute pairwise compatibility result between two people.

    Args:
        personA: First person
        personB: Second person
        compatibility_type: Group analysis context
        settings: Optional GroupSettings
    Returns:
        PairwiseResult with KPI scores, total score, and description.
    Raises:
        ValueError: if inputs are invalid
    """
    print("Computing pair:", personA.name, "and", personB.name)
    settings = settings or GroupSettings()
    # Validate tz to catch obvious issues early
    personA.validate_timezone()
    personB.validate_timezone()

    # Natal fetch (cached)
    nA = get_natal(personA.cache_key(), json.dumps(_person_to_natal_payload(personA)))
    nB = get_natal(personB.cache_key(), json.dumps(_person_to_natal_payload(personB)))

    kpis = _pair_kpi_scores(nA, nB, compatibility_type=compatibility_type, settings=settings)
    total = _pair_total_score(kpis, compatibility_type=compatibility_type)
    desc = describe_pair(kpis)

    return PairwiseResult(
        person1=personA.name,
        person2=personB.name,
        kpi_scores={k: round(float(v), 2) for k, v in kpis.items()},
        total_pair_score=round(float(total), 2),
        description=desc,
    )


# ----------------------------- Group aggregation -----------------------------
def _aggregate_group_kpis(pairs: List[PairwiseResult]) -> Dict[str, float]:
    acc: Dict[str, List[float]] = {k: [] for k in DEFAULT_KPIS}
    for pr in pairs:
        for k in DEFAULT_KPIS:
            acc[k].append(float(pr.kpi_scores.get(k, 50.0)))
    return {k: round(safe_mean(vs, 50.0), 2) for k, vs in acc.items()}


def _cohesion_metrics(pairs: List[PairwiseResult], people: List[PersonInput]) -> Dict[str, float]:
    scores = [float(p.total_pair_score) for p in pairs]
    base_mean = safe_mean(scores, 50.0)
    variance = float((pstdev(scores) if len(scores) >= 2 else 0.0) ** 2)
    # Map variance to a cohesion score (lower variance -> higher cohesion). Assume typical var in [0, 400].
    cohesion_from_var = clamp_0_100(100.0 - scale_0_100(variance, 0.0, 400.0))

    network = 0.0
    if _nx is not None and people:
        try:
            G = _nx.Graph()
            for p in people:
                G.add_node(p.name)
            for pr in pairs:
                G.add_edge(pr.person1, pr.person2, weight=float(pr.total_pair_score))
            # Approx cohesion: average weighted degree normalized by possible max
            degs = [sum(d.get("weight", 0.0) for _, _, d in G.edges(nb, data=True)) for nb in G.nodes]
            max_deg = (len(people) - 1) * 100.0 if len(people) > 1 else 100.0
            deg_norm = [scale_0_100(d, 0.0, max_deg) for d in degs]
            network = safe_mean(deg_norm, 0.0)
        except Exception:  # pragma: no cover - optional
            network = 0.0

    return {"variance": round(variance, 4), "cohesion_from_var": round(cohesion_from_var, 2), "network": round(network, 2)}


def _compose_total_group_score(base: float, metrics: Dict[str, float]) -> float:
    # Combine mean pair score with cohesion bonus in ±10 range
    cohesion = 0.5 * metrics.get("cohesion_from_var", 50.0) / 50.0 + 0.5 * metrics.get("network", 0.0) / 100.0
    cohesion_bonus = (cohesion - 0.5) * 20.0  # -10..+10 approximately
    return clamp_0_100(base + cohesion_bonus)


def _detect_outliers_cliques(pairs: List[PairwiseResult], people: List[PersonInput]) -> Dict[str, Any]:
    # Identify P10/P90 pairs
    sorted_pairs = sorted(pairs, key=lambda p: p.total_pair_score)
    n = len(sorted_pairs)
    if n == 0:
        return {"low_pairs": [], "high_pairs": [], "at_risk": [], "cliques": []}
    p10_idx = max(int(0.1 * n) - 1, 0)
    p90_idx = min(int(0.9 * n), n - 1)
    low_pairs = sorted_pairs[: p10_idx + 1]
    high_pairs = sorted_pairs[p90_idx:]

    # Integration risk: members with mean pair score < group mean - 1 SD
    by_member: Dict[str, List[float]] = {p.name: [] for p in people}
    for pr in pairs:
        by_member[pr.person1].append(float(pr.total_pair_score))
        by_member[pr.person2].append(float(pr.total_pair_score))
    member_means = {k: safe_mean(vs, 0.0) for k, vs in by_member.items()}
    vals = list(member_means.values())
    gmean = safe_mean(vals, 0.0)
    gsd = float(pstdev(vals)) if len(vals) >= 2 else 0.0
    at_risk = [k for k, v in member_means.items() if v < (gmean - gsd)]

    # Simple clique detection: threshold clustering on pair scores >= group mean
    clique_edges = {(pr.person1, pr.person2) for pr in pairs if pr.total_pair_score >= gmean}
    cliques: List[List[str]] = []
    if _nx is not None and clique_edges:
        try:
            G = _nx.Graph()
            for p in people:
                G.add_node(p.name)
            for a, b in clique_edges:
                G.add_edge(a, b)
            for comp in _nx.connected_components(G):
                if len(comp) > 1:
                    cliques.append(sorted(list(comp)))
        except Exception:  # pragma: no cover
            cliques = []

    return {
        "low_pairs": [(p.person1, p.person2, p.total_pair_score) for p in low_pairs],
        "high_pairs": [(p.person1, p.person2, p.total_pair_score) for p in high_pairs],
        "at_risk": at_risk,
        "cliques": cliques,
    }


def analyze_group(
    inputs: List[PersonInput],
    compatibility_type: CompatibilityType,
    *,
    settings: Optional[GroupSettings] = None,
) -> GroupResult:
    """Analyze a group and produce aggregated KPIs and a card payload.

    Args:
        inputs: List of PersonInput (>= 2)
        compatibility_type: Context type for weighting
        settings: Optional GroupSettings
    Returns:
        GroupResult with pairwise details, group KPIs, total score, summary, and card payload.
    Raises:
        ValueError: if inputs are invalid
    """
    settings = settings or GroupSettings()
    if not inputs or len(inputs) < 2:
        raise ValueError("At least two people are required for group analysis.")

    # Compute unordered pair results
    people = list(inputs)
    pairs_idx = list(combinations(range(len(people)), 2))
    pair_results: List[PairwiseResult] = []

    for i, j in pairs_idx:
        A, B = people[i], people[j]
        try:
            pr = compute_pair(A, B, compatibility_type, settings=settings)
        except Exception as e:  # robust: skip pair on error
            logger.warning("Skipping pair %s-%s due to error: %s", A.name, B.name, e)
            pr = PairwiseResult(person1=A.name, person2=B.name, kpi_scores={k: 0.0 for k in DEFAULT_KPIS}, total_pair_score=0.0, description="Invalid data; skipped")
        pair_results.append(pr)

    # Aggregate KPIs
    group_kpis_scores = _aggregate_group_kpis(pair_results)
    group_kpis = [
        GroupKPI(kpi=k, score=round(float(v), 2), description=f"Average {k} across pairs") for k, v in group_kpis_scores.items()
    ]

    # Cohesion metrics and total group score
    base = safe_mean([p.total_pair_score for p in pair_results], 0.0)
    metrics = _cohesion_metrics(pair_results, people)
    total_group = _compose_total_group_score(base, metrics)

    # Summary and card
    pair_sorted_by_score = sorted(pair_results, key=lambda p: p.total_pair_score, reverse=True)
    summary = short_summary_builder(total_group, group_kpis_scores, pair_sorted_by_score)
    payload = to_shareable_card(
        GroupResult(
            pairwise=pair_results,
            group_harmony=group_kpis,
            total_group_score=total_group,
            short_summary=summary,
            card_payload={},  # replaced below
        )
    )

    return GroupResult(
        pairwise=pair_results,
        group_harmony=group_kpis,
        total_group_score=round(float(total_group), 2),
        short_summary=summary,
        card_payload=payload,
    )


# -------------------------------- Presentation --------------------------------
def short_summary_builder(total_score: float, kpis: Dict[str, float], pairs_sorted: List[PairwiseResult]) -> str:
    label, _color = _badge_for_score(total_score)
    top_k = rank_top(kpis, 2, True)
    low_k = rank_top(kpis, 1, False)
    top_pair = f"{pairs_sorted[0].person1}–{pairs_sorted[0].person2}" if pairs_sorted else "N/A"
    low_pair = f"{pairs_sorted[-1].person1}–{pairs_sorted[-1].person2}" if pairs_sorted else "N/A"
    s = (
        f"Overall cohesion {round(total_score,2)}/100 ({label}). Strong in "
        f"{', '.join([k for k,_ in top_k])}. Watch {', '.join([k for k,_ in low_k])}. "
        f"Best synergy: {top_pair}. Potential friction: {low_pair}."
    )
    return s[:400]


def to_shareable_card(result: GroupResult) -> Dict[str, Any]:
    """Shape a JSON-serializable payload for frontend display.

    Returns a dict with keys: title, subtitle, badge_color, kpi_radar_data, pair_matrix,
    highlights, risks.
    """
    names = sorted({p.person1 for p in result.pairwise} | {p.person2 for p in result.pairwise})
    index = {name: idx for idx, name in enumerate(names)}
    n = len(names)
    # NxN matrix
    matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
    for pr in result.pairwise:
        i, j = index[pr.person1], index[pr.person2]
        matrix[i][j] = float(pr.total_pair_score)
        matrix[j][i] = float(pr.total_pair_score)

    kpi_map = {g.kpi: float(g.score) for g in result.group_harmony}
    label, color = _badge_for_score(result.total_group_score)

    top_pairs = sorted(result.pairwise, key=lambda p: p.total_pair_score, reverse=True)[:3]
    low_pairs = sorted(result.pairwise, key=lambda p: p.total_pair_score)[:3]

    payload = {
        "title": "Group Compatibility",
        "subtitle": f"Score {round(result.total_group_score,2)}/100 • {label}",
        "badge_color": color,
        "kpi_radar_data": [{"kpi": k, "score": float(v)} for k, v in kpi_map.items()],
        "pair_matrix": {"names": names, "matrix": matrix},
        "highlights": {
            "top_pairs": [
                {"pair": f"{p.person1}–{p.person2}", "score": float(p.total_pair_score)} for p in top_pairs
            ],
            "best_kpis": rank_top(kpi_map, 3, True),
        },
        "risks": {
            "low_pairs": [
                {"pair": f"{p.person1}–{p.person2}", "score": float(p.total_pair_score)} for p in low_pairs
            ],
            "low_kpis": rank_top(kpi_map, 3, False),
        },
        "__meta": {"version": "v1"},
    }
    return payload


def explain_pair_kpis(pair: PairwiseResult) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in pair.kpi_scores.items():
        if k == "Conflict Potential":
            if v >= 60:
                out[k] = "Balanced assertiveness; low friction expected."
            elif v >= 40:
                out[k] = "Some friction possible; align on conflict norms."
            else:
                out[k] = "High conflict risk; set clear boundaries early."
        elif k == "Emotional Harmony":
            out[k] = "Emotional cues and care patterns align well."
        elif k == "Communication Flow":
            out[k] = "Ideas and styles sync; feedback loops are smooth."
        else:
            out[k] = f"{k} at {v}/100 relative to group context."
    return out


# ---------------------------------- API ----------------------------------
def kpi_catalog() -> List[str]:
    return list(DEFAULT_KPIS)


def weights_profile(compatibility_type: CompatibilityType) -> Dict[str, float | str]:
    """Return normalized KPI weights for a given compatibility type.

    >>> round(sum(v for k,v in weights_profile('Family').items() if k!='__type'), 6)
    1.0
    """
    d: Dict[str, float | str] = dict(TYPE_KPI_WEIGHTS.get(compatibility_type, {}))
    d["__type"] = compatibility_type
    return d


# --------------------- API-layer shaping helpers (thin wrappers) ---------------------
def _to_person_input(p: Any) -> PersonInput:
    """Convert an incoming object/dict/Pydantic model into PersonInput.

    Accepts:
    - schemas.BirthPayload
    - dict with matching keys
    - any object exposing attributes like BirthPayload
    """
    if isinstance(p, PersonInput):
        return p
    try:
        if hasattr(p, "model_dump"):
            data = p.model_dump()
        elif isinstance(p, dict):
            data = dict(p)
        else:
            # Fallback to attribute extraction
            data = {
                "name": getattr(p, "name"),
                "dateOfBirth": getattr(p, "dateOfBirth"),
                "timeOfBirth": getattr(p, "timeOfBirth"),
                "placeOfBirth": getattr(p, "placeOfBirth"),
                "timeZone": getattr(p, "timeZone"),
                "latitude": getattr(p, "latitude"),
                "longitude": getattr(p, "longitude"),
            }
    except Exception as e:
        raise ValueError(f"Invalid person payload: {e}")
    return PersonInput(**data)


def analyze_group_api_payload(
    people: List[Any],
    compatibility_type: CompatibilityType,
    *,
    settings: Optional[GroupSettings] = None,
    max_people: int = 10,
) -> Dict[str, Any]:
    """High-level helper for API layer: validate, analyze, and shape data.

    Returns a dict shape compatible with GroupCompatibilityData:
    {"pairwise": [{person1, person2, kpi, score, description}],
     "groupHarmony": [{kpi, score, description}],
     "totalGroupScore": float(0..1)}
    """
    # Basic validations (keep API thin)
    if not is_supported_type(compatibility_type):
        raise ValueError(
            f"Unsupported group type '{compatibility_type}'. Allowed: {sorted(COMPATIBILITY_TYPES)}"
        )
    if people is None or len(people) < 2:
        raise ValueError("At least 2 people required")
    if len(people) > max_people:
        raise ValueError(f"Max {max_people} people supported in this endpoint")

    persons: List[PersonInput] = [_to_person_input(p) for p in people]

    grp = analyze_group(persons, compatibility_type, settings=settings)

    # Flatten pairwise: strongest KPI + normalize score to 0..1
    pair_rows: List[Dict[str, Any]] = []
    for pr in grp.pairwise:
        if pr.kpi_scores:
            top_kpi = max(pr.kpi_scores.items(), key=lambda kv: kv[1])[0]
        else:
            top_kpi = "n/a"
        norm_score = round(float(pr.total_pair_score) / 100.0, 2)
        pair_rows.append(
            {
                "person1": pr.person1,
                "person2": pr.person2,
                "kpi": top_kpi,
                "score": norm_score,
                "description": (pr.description[:140] if pr.description else None),
            }
        )

    harmony_rows: List[Dict[str, Any]] = []
    for gk in grp.group_harmony:
        harmony_rows.append(
            {
                "kpi": gk.kpi,
                "score": round(float(gk.score) / 100.0, 2),
                "description": (gk.description[:140] if gk.description else None),
            }
        )

    total_norm = round(float(grp.total_group_score) / 100.0, 2)

    return {
        "pairwise": pair_rows,
        "groupHarmony": harmony_rows,
        "totalGroupScore": total_norm,
    }


# --------------------------------- __main__ ---------------------------------
if __name__ == "__main__":  # pragma: no cover - demo only
    # Tiny demo group (3 people). This is illustrative; results depend on external cores.
    A = PersonInput(
        name="Amit",
        dateOfBirth="1991-07-14",
        timeOfBirth="22:35:00",
        placeOfBirth="Mumbai, IN",
        timeZone="Asia/Kolkata",
        latitude=19.0760,
        longitude=72.8777,
    )
    B = PersonInput(
        name="Riya",
        dateOfBirth="1993-02-20",
        timeOfBirth="06:10:00",
        placeOfBirth="Delhi, IN",
        timeZone="Asia/Kolkata",
        latitude=28.6139,
        longitude=77.2090,
    )
    C = PersonInput(
        name="Karan",
        dateOfBirth="1990-11-02",
        timeOfBirth="14:05:00",
        placeOfBirth="Pune, IN",
        timeZone="Asia/Kolkata",
        latitude=18.5204,
        longitude=73.8567,
    )
    grp = analyze_group([A, B, C], "Friendship Group")
    print(json.dumps(grp.model_dump(), indent=2))
