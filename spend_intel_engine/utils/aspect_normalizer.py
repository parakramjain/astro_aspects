from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

PLANET_ALIASES: Dict[str, str] = {
    "SUN": "SUN",
    "MOO": "MOO",
    "MOON": "MOO",
    "MER": "MER",
    "MERCURY": "MER",
    "VEN": "VEN",
    "VENUS": "VEN",
    "MAR": "MAR",
    "MARS": "MAR",
    "JUP": "JUP",
    "JUPITER": "JUP",
    "SAT": "SAT",
    "SATURN": "SAT",
    "URA": "URA",
    "URANUS": "URA",
    "NEP": "NEP",
    "NEPTUNE": "NEP",
    "PLU": "PLU",
    "PLUTO": "PLU",
    "ASC": "ASC",
}

ASPECT_ALIASES: Dict[str, str] = {
    "CON": "CON",
    "CONJ": "CON",
    "CONJUNCTION": "CON",
    "TRI": "TRI",
    "TRINE": "TRI",
    "SEX": "SEX",
    "SXT": "SEX",
    "SXTILE": "SEX",
    "SEXTILE": "SEX",
    "SXTL": "SEX",
    "SQR": "SQR",
    "SQ": "SQR",
    "SQUARE": "SQR",
    "OPP": "OPP",
    "OPPO": "OPP",
    "OPPOSITION": "OPP",
}


TOKEN_SPLIT = re.compile(r"[^A-Za-z]+")


def _canon_planet(token: str) -> Optional[str]:
    return PLANET_ALIASES.get(token.upper())


def _canon_aspect(token: str) -> Optional[str]:
    return ASPECT_ALIASES.get(token.upper())


def normalize_aspect_code(raw: str) -> Optional[str]:
    if not raw:
        return None
    parts = [p for p in TOKEN_SPLIT.split(raw.strip()) if p]
    if len(parts) < 3:
        return None

    p1 = _canon_planet(parts[0])
    aspect = _canon_aspect(parts[1])
    p2 = _canon_planet(parts[2])

    if not p1 or not aspect or not p2:
        return None
    return f"{p1} {aspect} {p2}"


def symmetric_keys(aspect_key: str) -> Tuple[str, str]:
    normalized = normalize_aspect_code(aspect_key)
    if not normalized:
        return aspect_key, aspect_key
    left, asp, right = normalized.split()
    return normalized, f"{right} {asp} {left}"
