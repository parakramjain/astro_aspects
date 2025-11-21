"""
Synastry (horoscope matchmaking) utilities.

This module computes cross-natal planetary aspects between two individuals and
scores relationship KPIs like Emotional, Communication, Chemistry, Stability,
and Elemental Balance to produce an overall compatibility score (0–10).

Public API
----------
calculate_synastry(person1_data: dict, person2_data: dict) -> dict
    End-to-end pipeline: positions -> aspects -> traits -> KPI scores -> output.

calculate_planetary_angles(pos1: dict[int,float], pos2: dict[int,float]) -> list[dict]
    Cross-match aspects between all planets of person1 and person2.

get_natal_characteristics(positions: dict[int,float]) -> dict
    Infer simple natal traits (elemental balance, modality, key highlights).

calculate_compatibility_scores(aspects: list[dict], traits1: dict, traits2: dict) -> dict
    Compute KPI scores and total (0–10) using aspect strengths and trait balance.

Notes
-----
- Uses astro_core.calc_planet_pos for positions (geocentric, ecliptic longitudes).
- Orbs for synastry use astro_core.NATAL_ASPECT_ORB_DEG as defaults.
- Ascendant is not computed in this version; Saturn↔Ascendant contribution is omitted.

Quick CLI Usage
----------------
Run directly:
    python services/synastry.py
This prints a sample JSON synastry result for two hard-coded people.

Programmatic example:
    from services.synastry import calculate_synastry
    result = calculate_synastry(person1_dict, person2_dict)
    # where each dict has keys: name, dateOfBirth, timeOfBirth, placeOfBirth, timeZone, latitude, longitude

Returned structure:
    {
       "person1": str,
       "person2": str,
       "aspects": [ {planet1, planet2, angle, aspect_type, orb}, ... ],
       "traits": {"person1": {...}, "person2": {...}},
       "kpi_scores": {kpi_name: 0..10, ...},
       "total_score": 0..10
    }
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import math
import os
import sys

# Ensure project root is on sys.path when running as a script (python services/synastry.py)
_HERE = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Swiss Ephemeris for planet names
import swisseph as swe  # type: ignore

# Project core
from astro_core.astro_core import (
    calc_planet_pos,
    ASPECTS,
    NATAL_ASPECT_ORB_DEG,
)

# ---------------------------- helpers ----------------------------
ASPECT_ANGLES = sorted(ASPECTS.keys())  # [0, 60, 90, 120, 180]
ASPECT_CODE_BY_ANGLE = ASPECTS  # int -> 'Con'/'Sxt'/'Sqr'/'Tri'/'Opp'

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
ELEMENT_BY_SIGN = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}
MODALITY_BY_SIGN = {
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
}

# Baseline modality definitions for interpretation
MODALITY_DEFINITIONS = {
    "Cardinal": "Initiating and action-oriented. Leads, starts new cycles, takes charge.",
    "Fixed": "Stable and persistent. Focused, dependable, sustains efforts and commitments.",
    "Mutable": "Adaptable and flexible. Learns quickly, bridges phases, versatile in approach.",
}

PRIORITY_PLANETS = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]
ALL_PLANETS = list(range(swe.SUN, swe.PLUTO + 1))

# Base scores for aspects (benefics higher)
ASPECT_BASE_SCORE = {
    "Con": 10.0,
    "Tri": 9.0,
    "Sxt": 7.5,
    "Opp": 6.0,
    "Sqr": 4.0,
}

# KPI weights (must sum to 1.0)
KPI_WEIGHTS = {
    "emotional": 0.25,
    "communication": 0.20,
    "chemistry": 0.25,
    "stability": 0.20,
    "elemental_balance": 0.10,
}


def _short(pid: int) -> str:
    return swe.get_planet_name(pid)[:3]


def _delta_circ(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return d if d <= 180.0 else 360.0 - d


def _dist_to_aspect(sep: float, aspect_angle: int) -> float:
    return _delta_circ(sep, float(aspect_angle))


def _sign_from_lon(lon: float) -> str:
    idx = int(math.floor((lon % 360.0) / 30.0))
    return SIGNS[idx]


def _normalize_name(name: str) -> str:
    # Canonical 3-letter codes used elsewhere in the project
    m = {
        "Moon": "Moo", "Mercury": "Mer", "Venus": "Ven", "Mars": "Mar",
        "Jupiter": "Jup", "Saturn": "Sat", "Uranus": "Ura", "Neptune": "Nep", "Pluto": "Plu",
        "Sun": "Sun",
    }
    return m.get(name, name[:3])


# ---------------------------- core computations ----------------------------

def calculate_planetary_angles(
    pos1: Dict[int, float],
    pos2: Dict[int, float],
    *,
    aspect_orbs: Dict[int, float] | None = None,
) -> List[Dict]:
    """
    Cross-aspects between every planet of person1 and person2.

    Returns a list of dict entries:
      { planet1, planet2, angle, aspect_type, orb }
    Only aspects within orb are included.
    """
    aspect_orbs = aspect_orbs or NATAL_ASPECT_ORB_DEG
    out: List[Dict] = []
    for pid1, lon1 in pos1.items():
        for pid2, lon2 in pos2.items():
            sep = _delta_circ(lon1, lon2)
            best_hit: Tuple[str, float, float] | None = None  # (aspect_code, angle, orb)
            for ang in ASPECT_ANGLES:
                code = ASPECT_CODE_BY_ANGLE[ang]
                orb_lim = float(aspect_orbs.get(ang, 0.0))
                orb = _dist_to_aspect(sep, ang)
                if orb <= orb_lim:
                    # keep the tightest orb for this pair
                    if best_hit is None or orb < best_hit[2]:
                        best_hit = (code, float(sep), float(orb))
            if best_hit:
                code, ang_deg, orb = best_hit
                out.append({
                    "planet1": _short(pid1),
                    "planet2": _short(pid2),
                    "angle": round(ang_deg, 2),
                    "aspect_type": code,
                    "orb": round(orb, 2),
                })
    # sort by orb tightness (ascending)
    out.sort(key=lambda r: (r["orb"], r["aspect_type"], r["planet1"], r["planet2"]))
    return out


def get_natal_characteristics(positions: Dict[int, float]) -> Dict:
    """
    Derive simple traits from planetary longitudes (no houses/dignities yet).

    - Elemental balance across all 10 planets
    - Modalities balance
    - Key highlights: Sun sign, Moon sign, Mercury sign, Venus sign, Mars sign
    """
    counts_element = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    counts_modality = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}

    key_signs: Dict[str, str] = {}

    for pid, lon in positions.items():
        sign = _sign_from_lon(lon)
        elem = ELEMENT_BY_SIGN[sign]
        mod = MODALITY_BY_SIGN[sign]
        counts_element[elem] += 1
        counts_modality[mod] += 1
        name = _short(pid)
        if pid in {swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS}:
            key_signs[name] = sign

    total = sum(counts_element.values()) or 1
    element_pct = {k: round(v / total, 3) for k, v in counts_element.items()}
    modality_pct = {k: round(v / total, 3) for k, v in counts_modality.items()}

    # Temperament: Fire+Air vs Earth+Water
    extro = element_pct["Fire"] + element_pct["Air"]
    intro = element_pct["Earth"] + element_pct["Water"]
    temperament = "Balanced"
    if extro - intro >= 0.2:
        temperament = "Extrovert-leaning"
    elif intro - extro >= 0.2:
        temperament = "Introvert-leaning"

    dominant_element = max(element_pct.items(), key=lambda x: x[1])[0]
    dominant_modality = max(modality_pct.items(), key=lambda x: x[1])[0]

    traits = {
        "sun_sign": key_signs.get("Sun"),
        "moon_sign": key_signs.get("Moo"),
        "mercury_sign": key_signs.get("Mer"),
        "venus_sign": key_signs.get("Ven"),
        "mars_sign": key_signs.get("Mar"),
        "element_balance": element_pct,
        "modality_balance": modality_pct,
        "temperament": temperament,
        "dominant_element": dominant_element,
        "dominant_modality": dominant_modality,
        "modality_baseline": MODALITY_DEFINITIONS,
        "modality_summary": f"Dominant modality: {dominant_modality} - {MODALITY_DEFINITIONS[dominant_modality]}",
    }
    return traits


def _score_aspect_list(aspects: List[Dict], pairs: List[Tuple[str, str]]) -> float:
    """Score 0-10 from a set of planet pairs using aspect base weights and orb tightness.

    pairs: list of acceptable planet short-code tuples (order-insensitive).
    """
    total = 0.0
    weight_sum = 0.0
    for a in aspects:
        p1, p2 = a["planet1"], a["planet2"]
        pair = (p1, p2)
        rpair = (p2, p1)
        if pair not in pairs and rpair not in pairs:
            continue
        base = ASPECT_BASE_SCORE.get(a["aspect_type"], 0.0)
        # find the max allowed orb used for the aspect angle from NATAL_ASPECT_ORB_DEG
        # We don't know the exact aspect angle here; approximate using the code mapping
        angle_map = {"Con": 0, "Sxt": 60, "Sqr": 90, "Tri": 120, "Opp": 180}
        max_orb = float(NATAL_ASPECT_ORB_DEG.get(angle_map[a["aspect_type"]], 6.0))
        tightness = max(0.0, 1.0 - float(a["orb"]) / max_orb)
        score = base * tightness  # 0..base
        total += score
        weight_sum += 10.0  # normalize to 10 per contributing aspect
    if weight_sum == 0.0:
        return 0.0
    # Normalize accumulated base*weights to 0..10 range
    return max(0.0, min(10.0, (total / weight_sum) * 10.0))


def _elemental_balance_score(traits1: Dict, traits2: Dict) -> float:
    e1 = traits1.get("element_balance", {})
    e2 = traits2.get("element_balance", {})
    # Manhattan distance over 4 elements; max distance is 2.0
    d = sum(abs(e1.get(k, 0.0) - e2.get(k, 0.0)) for k in ("Fire", "Earth", "Air", "Water"))
    return max(0.0, min(10.0, 10.0 * (1.0 - d / 2.0)))


def calculate_compatibility_scores(aspects: List[Dict], traits1: Dict, traits2: Dict) -> Dict:
    """
    Compute KPI scores 0-10 using cross-aspects and basic natal traits.
    """
    # Emotional: Moon↔Venus and Moon↔Moon
    emotional = _score_aspect_list(
        aspects,
        pairs=[("Moo", "Ven"), ("Moo", "Moo")],
    )

    # Communication: Mercury↔Mercury and Mercury↔Moon
    communication = _score_aspect_list(
        aspects,
        pairs=[("Mer", "Mer"), ("Mer", "Moo")],
    )

    # Chemistry: Venus↔Mars and Venus↔Sun
    chemistry = _score_aspect_list(
        aspects,
        pairs=[("Ven", "Mar"), ("Ven", "Sun")],
    )

    # Stability: Saturn↔Sun and Saturn↔Moon (Asc omitted)
    stability = _score_aspect_list(
        aspects,
        pairs=[("Sat", "Sun"), ("Sat", "Moo")],
    )

    # Elemental balance: similarity of distributions
    elemental_balance = _elemental_balance_score(traits1, traits2)

    scores = {
        "emotional": round(emotional, 2),
        "communication": round(communication, 2),
        "chemistry": round(chemistry, 2),
        "stability": round(stability, 2),
        "elemental_balance": round(elemental_balance, 2),
    }

    # Weighted total 0..10
    total = sum(scores[k] * KPI_WEIGHTS[k] for k in KPI_WEIGHTS)
    scores["total_score"] = round(total, 2)
    return scores


# ---------------------------- main pipeline ----------------------------

def _parse_person_input(person: Dict) -> Tuple[Dict, Dict]:
    """
    Convert person JSON into calc_planet_pos kwargs and a clean identity dict.
    Returns: (pos_kwargs, identity)
    """
    identity = {
        "name": person.get("name"),
        "placeOfBirth": person.get("placeOfBirth"),
        "timeZone": person.get("timeZone"),
        "latitude": person.get("latitude"),
        "longitude": person.get("longitude"),
    }
    kwargs = {
        "date": person.get("dateOfBirth"),
        "time": person.get("timeOfBirth"),
        "tz_str": person.get("timeZone", "UTC"),
    }
    return kwargs, identity


def calculate_synastry(person1_data: Dict, person2_data: Dict) -> Dict:
    """
    End-to-end synastry calculator.

    Input shape:
      { "person1": {...}, "person2": {...} }
    or direct two dicts passed as separate args.
    """
    # Allow callers to pass nested or direct dicts
    if "person1" in person1_data and "person2" in person2_data:
        person1_data = person1_data["person1"]
        person2_data = person2_data["person2"]

    p1_kwargs, p1_ident = _parse_person_input(person1_data)
    p2_kwargs, p2_ident = _parse_person_input(person2_data)

    # Step 1: positions
    pos1 = calc_planet_pos(**p1_kwargs)
    pos2 = calc_planet_pos(**p2_kwargs)

    # Step 2: aspects
    aspects = calculate_planetary_angles(pos1, pos2)

    # Step 3: traits
    traits1 = get_natal_characteristics(pos1)
    traits2 = get_natal_characteristics(pos2)

    # Step 4: KPIs
    kpi_scores = calculate_compatibility_scores(aspects, traits1, traits2)

    # Aggregate
    # Percentages for convenience (0..100)
    kpi_scores_pct = {k: round(v * 10.0, 1) for k, v in kpi_scores.items() if k != "total_score"}
    total_score_pct = round(kpi_scores["total_score"] * 10.0, 1)

    # Baseline guidance for interpreting scores
    baseline = {
        "average": 5.0,
        "good": 7.0,
        "excellent": 8.0,
        "notes": "0-4: low, ~5: average, 6-7: good, 8-10: strong"
    }

    output = {
        "person1": p1_ident["name"],
        "person2": p2_ident["name"],
        "aspects": aspects,
        "traits": {"person1": traits1, "person2": traits2},
        "kpi_scores": {k: v for k, v in kpi_scores.items() if k != "total_score"},
        "total_score": kpi_scores["total_score"],
        "kpi_scores_pct": kpi_scores_pct,
        "total_score_pct": total_score_pct,
        "baseline": baseline,
    }
    return output


if __name__ == "__main__":
    sample = {
        "person1": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
        "person2": {
            "name": "Riya",
            "dateOfBirth": "1993-02-20",
            "timeOfBirth": "06:10:00",
            "placeOfBirth": "Delhi, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 28.6139,
            "longitude": 77.2090,
        },
    }
    res = calculate_synastry(sample["person1"], sample["person2"])
    import json
    print(json.dumps(res, indent=2))
