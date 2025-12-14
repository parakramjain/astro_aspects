"""synastry_vedic_services
================================================================================
Vedic Ashtakoota (Gun Milan) synastry scorer.

This module computes the 8-koota compatibility score (0-36) between two natal
charts using classical Vedic rules centered on the Moon's position (Rashi and
Nakshatra). It returns a rich, traceable result suitable for APIs and tests.

Design principles
-----------------
- Pure functions with explicit inputs/outputs; no I/O in the core logic.
- Clear constants at top; logic below, modular helpers; deterministic results.
- Uses project astro core to obtain planetary longitudes and handles sidereal
  via Swiss Ephemeris configuration exposed by astro_core.

Public API
----------
- compute_ashtakoota_score(p1, p2, *, ayanamsa="lahiri", coordinate_system="sidereal",
                           strict_tradition=True, use_exceptions=False) -> dict
- explain_ashtakoota(result: dict) -> str

Internal helpers
----------------
- to_datetime_local, to_utc
- get_moon_longitude, tropical_to_sidereal
- moon_to_rashi, moon_to_nakshatra_index_and_pada
- score_* functions per koota
- sum_scores, validate_input

Notes
-----
Where exact classical tables vary among traditions, we document chosen tables
and keep the mapping in constants for easy review and refinement.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Tuple, List, Optional

from zoneinfo import ZoneInfo
import os
import sys

# Ensure project root is on sys.path when running as a script (python services/synastry_vedic_services.py)
_HERE = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import project astro core
try:
    from astro_core.astro_core import (
        calc_planet_pos as ac_calc_planet_pos,
        set_ayanamsha as ac_set_ayanamsha,
        current_ayanamsha_info as ac_current_ayanamsha_info,
    )
except Exception as e:  # pragma: no cover - surfaced to user
    raise ImportError(
        "Could not import project astro_core. Ensure the package path is correct.\n"
        f"Original error: {e}"
    )

# =============================== Constants ===============================

# Max points per koota
MAX_POINTS: Dict[str, int] = {
    "varna": 1,
    "vashya": 2,
    "tara": 3,
    "yoni": 4,
    "graha_maitri": 5,
    "gana": 6,
    "bhakoot": 7,
    "nadi": 8,
}

# Meaning/intent of each koota (used in API output and explanation)
KOOTA_MEANINGS: Dict[str, str] = {
    "varna": "Spiritual & mental balance, mutual respect, non-dominance",
    "vashya": "Control, dominance, mutual influence",
    "tara": "Health, longevity, general wellbeing",
    "yoni": "Physical attraction & intimacy",
    "graha_maitri": "Friendship, mental connection, intellectual sync",
    "gana": "Nature, temperament, and behavioral compatibility",
    "bhakoot": "Emotional harmony and empathy",
    "nadi": "Health of progeny, fertility, life energy",
}


def koota_compatibility_status(awarded: float, max_points: float) -> str:
    """Map a koota score to a simple compatibility status label.

    Statuses are derived purely from awarded/max ratio:
    - 0 -> "Dosha (bad)"
    - (0, 0.5) -> "Neutral"
    - [0.5, 0.75) -> "Average"
    - [0.75, 0.95) -> "Good"
    - [0.95, 1.0] -> "Excellent"
    """
    try:
        awarded_f = float(awarded)
        max_f = float(max_points)
    except Exception:
        return "Neutral"
    if max_f <= 0:
        return "Neutral"
    if awarded_f <= 0:
        return "Dosha (bad)"
    ratio = awarded_f / max_f
    if ratio >= 0.95:
        return "Excellent"
    if ratio >= 0.75:
        return "Good"
    if ratio >= 0.50:
        return "Average"
    return "Neutral"

# Total score interpretation bands (Gun Milan)
SCORE_BANDS = [
    (0.0, 17.5, "Challenging Match"),
    (18.0, 23.5, "Workable Match"),
    (24.0, 36.0, "Strong Match"),
]

ADVICE_MAP = {
    "Challenging Match": (
        "High risk of friction across key factors. Consult an astrologer for remedies and deeper analysis beyond Gun Milan."
    ),
    "Workable Match": (
        "Generally compatible with some gaps. With awareness and remedies, the partnership can succeed."
    ),
    "Strong Match": (
        "Excellent compatibility across most factors. A stable and harmonious match overall."
    ),
}

# Ayanamsa simple offsets (deg). Note: Real ayanamsa is epoch-dependent.
# We prefer using astro_core Swiss Ephemeris configuration. This mapping is
# provided for the tropical_to_sidereal helper only as a documented fallback.
AYANAMSA_OFFSETS_DEG = {
    "lahiri": 23.85,         # approximate modern-era value
    "krishnamurti": 23.95,   # approx
    "raman": 22.50,          # approx
}

# Rashi names by index (1..12)
RASHI_NAMES = {
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Varna hierarchy: Brahmin(4) > Kshatriya(3) > Vaishya(2) > Shudra(1)
VARNA_RANK_BY_RASHI = {
    # Water → Brahmin
    4: 4, 8: 4, 12: 4,
    # Fire → Kshatriya
    1: 3, 5: 3, 9: 3,
    # Earth → Vaishya
    2: 2, 6: 2, 10: 2,
    # Air → Shudra
    3: 1, 7: 1, 11: 1,
}
VARNA_NAME_BY_RANK = {1: "Shudra", 2: "Vaishya", 3: "Kshatriya", 4: "Brahmin"}

# Vashya categories by Moon sign (simplified classical mapping)
# Groups: Chatushpada (quadruped), Manav (human), Jalachara (water), Vanachara (wild), Keeta (insect)
VASHYA_GROUP_BY_RASHI = {
    1: "Chatushpada",   # Aries
    2: "Chatushpada",   # Taurus
    3: "Manav",         # Gemini
    4: "Jalachara",     # Cancer
    5: "Chatushpada",   # Leo (traditions vary; often manav for Leo rising, we use quadruped per instruction notes)
    6: "Manav",         # Virgo
    7: "Manav",         # Libra
    8: "Keeta",         # Scorpio
    9: "Vanachara",     # Sagittarius
    10: "Chatushpada",  # Capricorn (we ignore 0–15 vs 15–30 split; treat as quadruped throughout per instruction)
    11: "Manav",        # Aquarius
    12: "Jalachara",    # Pisces
}

# Vashya compatibility scoring matrix (0..2).
# Rule-of-thumb used:
# - Same group: 2
# - Friendly groups: 1 or 2 depending on traditional affinity
# - Unrelated/hostile: 0
VASHYA_SCORE: Dict[str, Dict[str, float]] = {
    "Chatushpada": {
        "Chatushpada": 2.0,
        "Manav": 1.0,
        "Jalachara": 0.5,
        "Vanachara": 1.0,
        "Keeta": 0.0,
    },
    "Manav": {
        "Chatushpada": 1.0,
        "Manav": 2.0,
        "Jalachara": 1.0,
        "Vanachara": 0.5,
        "Keeta": 0.0,
    },
    "Jalachara": {
        "Chatushpada": 0.5,
        "Manav": 1.0,
        "Jalachara": 2.0,
        "Vanachara": 0.0,
        "Keeta": 0.0,
    },
    "Vanachara": {
        "Chatushpada": 1.0,
        "Manav": 0.5,
        "Jalachara": 0.0,
        "Vanachara": 2.0,
        "Keeta": 0.0,
    },
    "Keeta": {
        "Chatushpada": 0.0,
        "Manav": 0.0,
        "Jalachara": 0.0,
        "Vanachara": 0.0,
        "Keeta": 2.0,
    },
}

# Planetary lords of Moon signs (traditional)
RASHI_LORD = {
    1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury",
    7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter",
}

# Classical planetary friendships (Parashara). Relations are directional; we compute mutual.
GRAHA_REL = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "neutrals": {"Mercury"}, "enemies": {"Venus", "Saturn"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "neutrals": {"Mars", "Jupiter", "Venus", "Saturn"}, "enemies": set()},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "neutrals": {"Venus", "Saturn"}, "enemies": {"Mercury"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "neutrals": {"Mars", "Jupiter", "Saturn"}, "enemies": {"Moon"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "neutrals": {"Saturn"}, "enemies": {"Mercury", "Venus"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "neutrals": {"Mars", "Jupiter"}, "enemies": {"Sun", "Moon"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "neutrals": {"Jupiter"}, "enemies": {"Sun", "Moon", "Mars"}},
}

# Gana mapping (chosen classical set; traditions vary)
NAKSHATRA_GANA = {
    # Deva (9)
    0: "Deva", 4: "Deva", 6: "Deva", 7: "Deva", 12: "Deva", 14: "Deva", 16: "Deva", 21: "Deva", 26: "Deva",
    # Manushya (6)
    1: "Manushya", 2: "Manushya", 3: "Manushya", 11: "Manushya", 20: "Manushya", 25: "Manushya",
    # Rakshasa (12)
    5: "Rakshasa", 8: "Rakshasa", 9: "Rakshasa", 10: "Rakshasa", 13: "Rakshasa", 15: "Rakshasa",
    17: "Rakshasa", 18: "Rakshasa", 19: "Rakshasa", 22: "Rakshasa", 23: "Rakshasa", 24: "Rakshasa",
}

# Gana scoring matrix (0..6)
GANA_SCORE = {
    "Deva": {"Deva": 6.0, "Manushya": 5.0, "Rakshasa": 1.0},
    "Manushya": {"Deva": 5.0, "Manushya": 6.0, "Rakshasa": 3.0},
    "Rakshasa": {"Deva": 1.0, "Manushya": 3.0, "Rakshasa": 6.0},
}

# Bhakoot: inauspicious distance pairs (♂→♀ and ♀→♂) 2/12, 6/8, 5/9
BHAKOOT_BAD_PAIRS = {(2, 12), (12, 2), (6, 8), (8, 6), (5, 9), (9, 5)}
BHAKOOT_GOODSETS = {
    # Auspicious 1/1, 3/11, 4/10, 7/7. We'll detect by distance check rather than pairs.
}

# Nadi mapping (classical cycle: Adi, Madhya, Antya) – pattern repeats every 9 nakshatras.
# Many sources map as: 0:Adi,1:Madhya,2:Antya, 3:Adi,4:Madhya,5:Antya, ...
NAKSHATRA_NADI = {i: ("Adi" if (i % 3) == 0 else ("Madhya" if (i % 3) == 1 else "Antya")) for i in range(27)}

# Yoni mapping (chosen commonly cited mapping; reviewable constants)
NAKSHATRA_YONI = {
    0: "Horse", 1: "Elephant", 2: "Sheep", 3: "Serpent", 4: "Serpent", 5: "Dog",
    6: "Cat", 7: "Sheep", 8: "Cat", 9: "Rat", 10: "Rat", 11: "Cow",
    12: "Buffalo", 13: "Tiger", 14: "Buffalo", 15: "Tiger", 16: "Deer", 17: "Deer",
    18: "Dog", 19: "Monkey", 20: "Mongoose", 21: "Monkey", 22: "Lion", 23: "Horse",
    24: "Lion", 25: "Cow", 26: "Elephant",
}

# Yoni compatibility classes -> score (0..4). Matrix is symmetric; define classes.
# Same → 4, Friendly → 3, Neutral → 2, Enemy → 0
YONI_FRIENDS = {
    "Horse": {"Horse", "Elephant", "Deer"},
    "Elephant": {"Elephant", "Cow"},
    "Sheep": {"Sheep", "Buffalo", "Cow"},
    "Serpent": {"Serpent", "Cat"},
    "Dog": {"Dog"},
    "Cat": {"Cat"},
    "Rat": {"Rat"},
    "Cow": {"Cow", "Elephant", "Sheep"},
    "Buffalo": {"Buffalo", "Sheep"},
    "Tiger": {"Tiger", "Lion"},
    "Deer": {"Deer", "Horse"},
    "Monkey": {"Monkey"},
    "Mongoose": {"Mongoose"},
    "Lion": {"Lion", "Tiger"},
}
YONI_ENEMIES = {
    "Horse": {"Tiger", "Lion", "Dog", "Serpent"},
    "Elephant": {"Lion", "Tiger"},
    "Sheep": {"Tiger", "Lion"},
    "Serpent": {"Mongoose", "Horse", "Peacock" if False else "Lion"},  # mongoose is natural enemy; include lion as adverse
    "Dog": {"Cat"},
    "Cat": {"Dog", "Rat"},
    "Rat": {"Cat"},
    "Cow": {"Tiger", "Lion"},
    "Buffalo": {"Lion", "Tiger"},
    "Tiger": {"Cow", "Sheep", "Buffalo"},
    "Deer": {"Tiger", "Lion"},
    "Monkey": set(),
    "Mongoose": {"Serpent"},
    "Lion": {"Elephant", "Cow", "Sheep", "Buffalo"},
}


# =============================== Data types ===============================

@dataclass(frozen=True)
class PersonInput:
    name: str
    dateOfBirth: str
    timeOfBirth: str
    placeOfBirth: str
    timeZone: str
    latitude: float
    longitude: float


# =============================== Helpers ===============================

def validate_input(person: dict) -> None:
    """Validate that the input dict has required keys and reasonable values.

    Raises ValueError with a clear message on problems.
    """
    required = [
        "name", "dateOfBirth", "timeOfBirth", "placeOfBirth",
        "timeZone", "latitude", "longitude",
    ]
    missing = [k for k in required if k not in person]
    if missing:
        raise ValueError(f"Missing keys in person: {missing}")
    try:
        ZoneInfo(person["timeZone"])  # validate tz
    except Exception:
        raise ValueError(f"Invalid timeZone: {person['timeZone']}")
    lat = float(person["latitude"])
    lon = float(person["longitude"])
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude out of bounds: {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"longitude out of bounds: {lon}")
    # Date/time strings (ISO) will be parsed later; errors will surface clearly


def to_datetime_local(date_str: str, time_str: str, tz_str: str) -> datetime:
    """Parse local date/time strings with ZoneInfo timezone.

    Args:
        date_str: 'YYYY-MM-DD'
        time_str: 'HH:MM:SS'
        tz_str: an IANA tz string like 'Asia/Kolkata'
    Returns:
        timezone-aware datetime in the given local timezone.
    """
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        raise ValueError(f"Invalid timeZone: {tz_str}")
    dt_local = datetime.fromisoformat(f"{date_str}T{time_str}")
    if dt_local.tzinfo is not None:
        # normalize to the provided tz if the input had one
        return dt_local.astimezone(tz)
    return dt_local.replace(tzinfo=tz)


def to_utc(dt_local: datetime, tz_str: str) -> datetime:
    """Convert a local timezone-aware datetime to UTC (aware)."""
    if dt_local.tzinfo is None:
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            raise ValueError(f"Invalid timeZone: {tz_str}")
        dt_local = dt_local.replace(tzinfo=tz)
    return dt_local.astimezone(timezone.utc)


def tropical_to_sidereal(lon_deg: float, ayanamsa: str = "lahiri") -> float:
    """Convert a tropical ecliptic longitude to sidereal using a fixed offset.

    Note: Real ayanamsa depends on epoch; this helper only provides a
    documented constant-offset conversion for completeness. The main pipeline
    prefers astro_core Swiss Ephemeris sidereal handling.
    """
    offs = AYANAMSA_OFFSETS_DEG.get(ayanamsa.lower())
    if offs is None:
        raise ValueError(f"Unsupported ayanamsa for fixed-offset conversion: {ayanamsa}")
    x = (lon_deg - offs) % 360.0
    return x if x >= 0 else x + 360.0


def get_moon_longitude(
    dt_utc: datetime,
    lat: float,
    lon: float,
    ayanamsa: str = "lahiri",
    coordinate_system: str = "sidereal",
) -> float:
    """Return Moon ecliptic longitude (deg) per requested coordinate system.

    We call project astro_core.calc_planet_pos with tz_str="UTC" and override
    ayanamsa mode by coordinate_system. Returns longitude in degrees 0–360.
    """
    # Convert UTC datetime into date/time strings for astro_core API
    d = dt_utc.astimezone(timezone.utc)
    date_str = d.date().isoformat()
    time_str = d.time().replace(microsecond=0).isoformat()

    mode = "sidereal" if coordinate_system.lower() == "sidereal" else "tropical"
    # Map ayanamsa name to astro_core names
    name_map = {"lahiri": "Lahiri", "krishnamurti": "Krishnamurti", "raman": "Raman"}
    ayan_name = name_map.get(ayanamsa.lower(), "Lahiri")

    # Configure via per-call override
    pos = ac_calc_planet_pos(
        date_str,
        time_str,
        tz_str="UTC",
        ayanamsha_mode=mode,
        ayanamsha_name=ayan_name,
    )

    # Swiss IDs: 0..9 (Sun..Pluto); Moon is 1 in Swiss Ephemeris.
    # astro_core returns dict[int,float]; index 1 corresponds to the Moon.
    moon_id = 1
    if moon_id not in pos:
        raise ValueError("Ephemeris call did not return Moon position.")
    return float(pos[moon_id]) % 360.0


def moon_to_rashi(moon_lon_deg: float) -> int:
    """Moon longitude (deg) -> Rashi index (1..12), Aries=1."""
    rashi = int(moon_lon_deg // 30.0) + 1
    return 12 if rashi == 13 else rashi


def moon_to_nakshatra_index_and_pada(moon_lon_deg: float) -> Tuple[int, int]:
    """Compute nakshatra index (0..26) and pada (1..4) for Moon.

    Nakshatra size = 13°20' = 13.333... degrees. Pada is quarter.
    """
    segment = 360.0 / 27.0
    idx = int((moon_lon_deg % 360.0) // segment)
    # pada within the nakshatra
    intra = (moon_lon_deg % segment) / segment  # 0..1
    pada = int(intra * 4.0) + 1
    if pada > 4:
        pada = 4
    return idx, pada


# ============================ Koota scorers =============================

def score_varna(rashi1: int, rashi2: int) -> Dict:
    """Varna scoring (out of 1).

    Rule: if groom's varna rank ≥ bride's varna rank, award 1 else 0.
    We don't determine gender here; instead, interpret person1 as "groom" and
    person2 as "bride" for deterministic scoring. Callers can swap to test.
    """
    v1 = VARNA_RANK_BY_RASHI[rashi1]
    v2 = VARNA_RANK_BY_RASHI[rashi2]
    awarded = 1.0 if v1 >= v2 else 0.0
    return {
        "awarded": awarded,
        "max": MAX_POINTS["varna"],
        "detail": {"varna1": VARNA_NAME_BY_RANK[v1], "varna2": VARNA_NAME_BY_RANK[v2], "rank1": v1, "rank2": v2},
    }


def score_vashya(rashi1: int, rashi2: int) -> Dict:
    """Vashya scoring (out of 2) using group compatibility matrix.
    """
    g1 = VASHYA_GROUP_BY_RASHI[rashi1]
    g2 = VASHYA_GROUP_BY_RASHI[rashi2]
    awarded = float(VASHYA_SCORE.get(g1, {}).get(g2, 0.0))
    return {"awarded": awarded, "max": MAX_POINTS["vashya"], "detail": {"group1": g1, "group2": g2}}


def _tara_group(n1: int, n2: int) -> Tuple[int, int]:
    # forward distance from n1 to n2 in 0..26 (cyclic)
    d_fwd = (n2 - n1) % 27
    d_rev = (n1 - n2) % 27
    # use minimal cyclic distance for group determination per instruction
    diff = min(d_fwd, d_rev)
    return diff, diff % 9


def score_tara(nak1: int, nak2: int, *, strict_tradition: bool = True) -> Dict:
    """Tara (Dina) scoring (out of 3).

    diff = cyclic abs distance in 0..26; group = diff % 9.
    Good groups: {1,3,4,6,8,0} → 3 points.
    Medium groups (when strict_tradition=False): {2,5,7} → 1.5 points.
    Bad groups: others → 0.
    """
    diff, group = _tara_group(nak1, nak2)
    good = {1, 3, 4, 6, 8, 0}
    medium = {2, 5, 7}
    if group in good:
        awarded = 3.0
        cls = "good"
    elif (not strict_tradition) and (group in medium):
        awarded = 1.5
        cls = "medium"
    else:
        awarded = 0.0
        cls = "bad"
    return {"awarded": awarded, "max": MAX_POINTS["tara"], "detail": {"diff": diff, "group": group, "class": cls}}


def score_yoni(nak1: int, nak2: int) -> Dict:
    """Yoni scoring (out of 4) using yoni mapping and friendly/enemy sets.
    """
    y1 = NAKSHATRA_YONI[nak1]
    y2 = NAKSHATRA_YONI[nak2]
    if y1 == y2:
        awarded = 4.0
        cls = "match"
    elif y2 in YONI_FRIENDS.get(y1, set()) and y1 in YONI_FRIENDS.get(y2, set()):
        awarded = 3.0
        cls = "friendly"
    elif y2 in YONI_ENEMIES.get(y1, set()) or y1 in YONI_ENEMIES.get(y2, set()):
        awarded = 0.0
        cls = "enemy"
    else:
        awarded = 2.0
        cls = "neutral"
    return {"awarded": awarded, "max": MAX_POINTS["yoni"], "detail": {"yoni1": y1, "yoni2": y2, "class": cls}}


def _graha_relation(a: str, b: str) -> Tuple[str, float]:
    ra = GRAHA_REL[a]
    rb = GRAHA_REL[b]
    # Determine mutual class
    def rel_to(x: str, relmap: dict) -> str:
        if x in relmap["friends"]:
            return "friend"
        if x in relmap["enemies"]:
            return "enemy"
        return "neutral"
    a_to_b = rel_to(b, ra)
    b_to_a = rel_to(a, rb)

    # Scoring guideline (out of 5)
    if a_to_b == "friend" and b_to_a == "friend":
        return "mutual_friend", 5.0
    if "enemy" in (a_to_b, b_to_a):
        if a_to_b == "enemy" and b_to_a == "enemy":
            return "mutual_enemy", 0.0
        return "enemy_mix", 2.0
    # At least one friend and the other neutral
    if (a_to_b == "friend" and b_to_a == "neutral") or (b_to_a == "friend" and a_to_b == "neutral"):
        return "friend_neutral", 4.0
    # neutral/neutral
    return "mutual_neutral", 3.0


def score_graha_maitri(rashi1: int, rashi2: int) -> Dict:
    """Graha Maitri (Rasyadhipati) scoring (out of 5).
    """
    lord1 = RASHI_LORD[rashi1]
    lord2 = RASHI_LORD[rashi2]
    relation, awarded = _graha_relation(lord1, lord2)
    return {
        "awarded": awarded,
        "max": MAX_POINTS["graha_maitri"],
        "detail": {"lord1": lord1, "lord2": lord2, "relation": relation},
    }


def score_gana(nak1: int, nak2: int) -> Dict:
    """Gana scoring (out of 6) using classical matrix."""
    g1 = NAKSHATRA_GANA[nak1]
    g2 = NAKSHATRA_GANA[nak2]
    awarded = float(GANA_SCORE[g1][g2])
    return {"awarded": awarded, "max": MAX_POINTS["gana"], "detail": {"gana1": g1, "gana2": g2}}


def _sign_distance(a: int, b: int) -> int:
    return (b - a) % 12 or 12  # 1..12 distance wrapping


def score_bhakoot(rashi1: int, rashi2: int) -> Dict:
    """Bhakoot scoring (out of 7) using sign distances.

    Inauspicious pairs include 2/12, 6/8, 5/9 → 0 points. Auspicious: 1/1, 3/11, 4/10, 7/7 → 7 points.
    """
    d12 = _sign_distance(rashi1, rashi2)
    d21 = _sign_distance(rashi2, rashi1)
    pair = (d12, d21)
    # Check bad pairs by distance set, irrespective of order
    if (d12, d21) in BHAKOOT_BAD_PAIRS:
        awarded = 0.0
        status = "inauspicious"
    else:
        # Check auspicious families
        good = False
        if d12 == 1 and d21 == 1:
            good = True
        elif {d12, d21} == {3, 11}:
            good = True
        elif {d12, d21} == {4, 10}:
            good = True
        elif d12 == 7 and d21 == 7:
            good = True
        if good:
            awarded = 7.0
            status = "auspicious"
        else:
            # Neutral: often scored as full or partial depending on school; we award full unless in explicit bad set.
            awarded = 7.0
            status = "neutral_or_ok"
    return {"awarded": awarded, "max": MAX_POINTS["bhakoot"], "detail": {"distance_m": d12, "distance_f": d21, "status": status}}


def score_nadi(nak1: int, nak2: int, *, use_exceptions: bool = False) -> Dict:
    """Nadi scoring (out of 8). Same Nadi → 0 else 8. Exceptions toggle is provided but off by default."""
    n1 = NAKSHATRA_NADI[nak1]
    n2 = NAKSHATRA_NADI[nak2]
    if n1 == n2:
        awarded = 0.0
    else:
        awarded = 8.0
    # Exceptions (gotra etc.) not implemented; this is a placeholder flag
    return {"awarded": awarded, "max": MAX_POINTS["nadi"], "detail": {"nadi1": n1, "nadi2": n2, "exceptions": bool(use_exceptions)}}


def sum_scores(parts: Dict[str, Dict]) -> Dict:
    """Aggregate scores and enforce rounding to at most 1 decimal."""
    total = 0.0
    fixed = {}
    for k, v in parts.items():
        awarded = float(v.get("awarded", 0.0))
        awarded = round(awarded * 2) / 2.0  # round to nearest 0.5
        fixed[k] = {**v, "awarded": awarded, "max": int(v.get("max", MAX_POINTS.get(k, 0)))}
        total += awarded
    total = round(total, 1)
    return {"scores": fixed, "total": total}


def interpret_total_score(total: float) -> Dict:
    """Classify total Gun Milan score into standard match bands.

    Args:
        total (float): Total Ashtakoota score (0–36)

    Returns:
        dict with keys: total, band, range[low, high], advice.
    """
    total = round(total, 1)
    for low, high, label in SCORE_BANDS:
        if low <= total <= high:
            return {
                "total": total,
                "band": label,
                "range": [low, high],
                "advice": ADVICE_MAP[label],
            }
    return {
        "total": total,
        "band": "Undefined",
        "range": [0.0, 36.0],
        "advice": "Score out of expected range. Please verify inputs.",
    }


# ============================ High-level API ============================

def _namecase_ayan(ayanamsa: str) -> str:
    return {"lahiri": "Lahiri", "krishnamurti": "Krishnamurti", "raman": "Raman"}.get(ayanamsa.lower(), "Lahiri")


def derive_non_scoring_insights(person1_meta: dict, person2_meta: dict) -> Dict:
    """Produce qualitative, non-scoring notes based on graha maitri and a few planet pairs.

    We look at Moon sign lords relation and optionally Sun, Venus, Mars sign-lord relations.
    """
    l1 = RASHI_LORD[person1_meta["rashi"]]
    l2 = RASHI_LORD[person2_meta["rashi"]]
    rel_moon, _ = _graha_relation(l1, l2)

    return {
        "moon_lord_relation": rel_moon,
        "notes": [
            f"Moon lord relation: {l1} vs {l2} → {rel_moon}",
        ],
    }


def compute_ashtakoota_score(
    p1: dict,
    p2: dict,
    *,
    ayanamsa: str = "lahiri",
    coordinate_system: str = "sidereal",
    strict_tradition: bool = True,
    use_exceptions: bool = False,
) -> Dict:
    """Compute Ashtakoota (Gun Milan) score and breakdown.

    Args:
      p1, p2: Person dicts with required keys as per schema.
      ayanamsa: ayanamsa name; defaults to 'lahiri'.
      coordinate_system: 'sidereal' (default) or 'tropical'.
      strict_tradition: When True, keeps integer scoring (e.g., Tara no 1.5).
      use_exceptions: Nadi exceptions toggle (non-functional placeholder, default off).

    Returns:
      dict with meta, scores per koota, and total out of 36.
    """
    validate_input(p1)
    validate_input(p2)

    # Times
    dt1_local = to_datetime_local(p1["dateOfBirth"], p1["timeOfBirth"], p1["timeZone"])
    dt2_local = to_datetime_local(p2["dateOfBirth"], p2["timeOfBirth"], p2["timeZone"])
    dt1_utc = to_utc(dt1_local, p1["timeZone"])  # aware
    dt2_utc = to_utc(dt2_local, p2["timeZone"])  # aware

    # Moon longitudes (sidereal/tropical per request)
    moon1 = get_moon_longitude(dt1_utc, float(p1["latitude"]), float(p1["longitude"]), ayanamsa, coordinate_system)
    moon2 = get_moon_longitude(dt2_utc, float(p2["latitude"]), float(p2["longitude"]), ayanamsa, coordinate_system)

    # Derived
    r1 = moon_to_rashi(moon1)
    r2 = moon_to_rashi(moon2)
    nak1, pada1 = moon_to_nakshatra_index_and_pada(moon1)
    nak2, pada2 = moon_to_nakshatra_index_and_pada(moon2)

    # Koota scores
    parts: Dict[str, Dict] = {}
    parts["varna"] = score_varna(r1, r2)
    parts["vashya"] = score_vashya(r1, r2)
    parts["tara"] = score_tara(nak1, nak2, strict_tradition=strict_tradition)
    parts["yoni"] = score_yoni(nak1, nak2)
    parts["graha_maitri"] = score_graha_maitri(r1, r2)
    parts["gana"] = score_gana(nak1, nak2)
    parts["bhakoot"] = score_bhakoot(r1, r2)
    parts["nadi"] = score_nadi(nak1, nak2, use_exceptions=use_exceptions)

    agg = sum_scores(parts)

    # Attach koota meanings + status for API consumers (non-breaking additive fields)
    for k, v in agg.get("scores", {}).items():
        if not isinstance(v, dict):
            continue
        meaning = KOOTA_MEANINGS.get(k)
        if meaning:
            v.setdefault("meaning", meaning)
        v.setdefault("compatibility_status", koota_compatibility_status(v.get("awarded", 0.0), v.get("max", MAX_POINTS.get(k, 0))))
    meta = {
        "ayanamsa": ayanamsa,
        "coordinate_system": coordinate_system,
        "person1": {
            "name": p1["name"],
            "moon_lon": round(moon1, 4),
            "rashi": r1,
            "nakshatra_index": nak1,
            "pada": pada1,
        },
        "person2": {
            "name": p2["name"],
            "moon_lon": round(moon2, 4),
            "rashi": r2,
            "nakshatra_index": nak2,
            "pada": pada2,
        },
    }
    insights = derive_non_scoring_insights(meta["person1"], meta["person2"])
    summary = interpret_total_score(agg["total"])  # band classification

    return {"meta": meta, **agg, "insights": insights, "summary": summary}


def explain_ashtakoota(result: Dict) -> str:
    """Build a human-readable explanation per koota with awarded points, reasons, and factor descriptions."""
    lines: List[str] = []
    s = result.get("scores", {})

    def kline(key: str, title: str, detail_keys: List[Tuple[str, str]] | None = None) -> None:
        if key not in s:
            return
        awarded = s[key]["awarded"]
        maxp = s[key]["max"]
        detail = s[key].get("detail", {})
        extras = []
        if detail_keys:
            for dk, label in detail_keys:
                if dk in detail:
                    extras.append(f"{label}: {detail[dk]}")
        extra = f" ({'; '.join(extras)})" if extras else ""
        desc = KOOTA_MEANINGS.get(key)
        desc_txt = f" - {desc}" if desc else ""
        lines.append(f"{title}: {awarded}/{maxp}{extra}{desc_txt}")

    kline("varna", "Varna", [("varna1", "P1"), ("varna2", "P2")])
    kline("vashya", "Vashya", [("group1", "P1"), ("group2", "P2")])
    if "tara" in s:
        d = s["tara"]["detail"]
        desc_txt = " - " + KOOTA_MEANINGS["tara"]
        lines.append(
            f"Tara: {s['tara']['awarded']}/{s['tara']['max']} (diff={d.get('diff')}, group={d.get('group')}, class={d.get('class')}){desc_txt}"
        )
    kline("yoni", "Yoni", [("yoni1", "P1"), ("yoni2", "P2"), ("class", "class")])
    kline("graha_maitri", "Graha Maitri", [("lord1", "P1"), ("lord2", "P2"), ("relation", "relation")])
    kline("gana", "Gana", [("gana1", "P1"), ("gana2", "P2")])
    if "bhakoot" in s:
        d = s["bhakoot"]["detail"]
        desc_txt = " - " + KOOTA_MEANINGS["bhakoot"]
        lines.append(
            f"Bhakoot: {s['bhakoot']['awarded']}/{s['bhakoot']['max']} (m→f={d.get('distance_m')}, f→m={d.get('distance_f')}, {d.get('status')}){desc_txt}"
        )
    kline("nadi", "Nadi", [("nadi1", "P1"), ("nadi2", "P2")])
    lines.append(f"Total: {result.get('total', 0)}/36")
    summary = interpret_total_score(result.get("total", 0))  # band classification
    lines.append(f"Summary: {summary['band']} - {summary['advice']}")
    return "\n".join(lines)


# ============================== Self-checks =============================

if __name__ == "__main__":
    # Sample input from instructions
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

    res = compute_ashtakoota_score(sample["person1"], sample["person2"], ayanamsa="lahiri", coordinate_system="sidereal")
    print(res)
    print("\n-- Explanation --\n")
    print(explain_ashtakoota(res))

    # Basic assertions (lightweight sanity)
    assert isinstance(res, dict)
    assert "scores" in res and "total" in res
    assert 0.0 <= float(res["total"]) <= 36.0
    for k in MAX_POINTS.keys():
        assert k in res["scores"], f"Missing koota in result: {k}"
        v = res["scores"][k]
        assert 0.0 <= float(v["awarded"]) <= float(v["max"]) <= MAX_POINTS[k]
        assert "meaning" in v and isinstance(v["meaning"], str) and v["meaning"], f"Missing meaning for koota: {k}"
        assert v.get("compatibility_status") in {"Dosha (bad)", "Neutral", "Average", "Good", "Excellent"}, f"Bad status for koota: {k}"
# ============================ Constants =============================
