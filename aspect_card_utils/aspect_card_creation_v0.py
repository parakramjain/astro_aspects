#!/usr/bin/env python3
"""
Generate Aspect Card skeletons for all planet–aspect–planet combinations.

- One JSON per card under ./kb/aspects/
- Master ./kb/index.json listing all card ids
- Stable ID format: {P1}_{ASPECT}_{P2}__v1.0.0 (3-letter codes)
- Canonicalizes planet order (outer ➜ inner) for symmetric aspects

Edit the FACETS/LOCALES templates to your taste; you can safely re-run.
"""

from __future__ import annotations
import json, os, sys
from dataclasses import dataclass, asdict
import csv
from datetime import date
from typing import Dict, List, Tuple
# import all the functions and variables from vedic_kb.py
from aspect_card_utils.vedic_kb import *
from aspect_card_utils.vedic_kb import _compose_core, _compose_facets, _compose_actionables, _keywords, _aspect_valence_tags, _weights_hint, _risk_notes, _locales, _retrieval_blocks, _modifiers

# -----------------------------
# Config — tweak as you like
# -----------------------------

OUTPUT_DIR = "./kb/aspects"
INDEX_PATH = "./kb/index.json"
VERSION = "v1.0.0"
APPLIES_TO = ["natal", "transit", "progressed"]
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Default to repo-relative CSV (first two columns: Aspect, Life event)
LIFE_EVENTS_CSV = os.path.normpath(os.path.join(_BASE_DIR, "./kb/Life_Events_Aspects_structured.csv"))

# Planets in outer→inner rank for canonical ordering
PLANETS: List[str] = [
    "Pluto", "Neptune", "Uranus", "Saturn", "Jupiter",
    "Mars", "Venus", "Mercury", "Moon", "Sun"
]
# If you use True Node, add "Node" (and set a rank)
# PLANETS.insert(0, "Node")



# Default orb hints (degrees) by aspect type
DEFAULT_ORB_DEG: Dict[str, int] = {
    "CON": 8, "OPP": 7, "SQR": 6, "TRI": 6, "SXT": 4,
    # "QNC": 3, "QNT": 2, "SSX": 2, "SSQ": 2, "SES": 2, "PAR": 2, "CPA": 2,
}

# Planet weights (tweak later; used only as hints)
PLANET_WEIGHT: Dict[str, float] = {
    "Sun": 1.00, "Moon": 1.00, "Mercury": 0.85, "Venus": 0.85, "Mars": 0.85,
    "Jupiter": 0.90, "Saturn": 0.95, "Uranus": 0.75, "Neptune": 0.70, "Pluto": 0.70,
    # "Node": 0.65,
}

CLASS_WEIGHT = {"natal": 1.0, "transit": 0.9, "progressed": 0.8}

# Whether to include self-aspects (e.g., Sun Conj Sun in transit-to-natal)
INCLUDE_SELF_ASPECTS = True

# If True, skip generating both (A,B) and (B,A) by enforcing canonical ordering (outer→inner)
CANONICALIZE_ORDER = False

# -----------------------------
# Helpers
# -----------------------------

PLANET_RANK = {p: i for i, p in enumerate(PLANETS)}  # lower index = more outer

def to_code_planet(name: str) -> str:
    return name[:3].upper()

def id_for(p1: str, asp_code: str, p2: str) -> str:
    return f"{to_code_planet(p1)}_{asp_code}_{to_code_planet(p2)}__{VERSION}"

def canonical_pair(a: str, b: str) -> Tuple[str, str]:
    """Outer→inner for symmetric aspects. Equal rank falls back to alpha."""
    ra, rb = PLANET_RANK[a], PLANET_RANK[b]
    if ra < rb:   # a is more outer
        return (a, b)
    if rb < ra:
        return (b, a)
    s = sorted([a, b])
    return (s[0], s[1])

# -----------------------------
# Aspect Card Skeleton
# -----------------------------

@dataclass
class AspectCard:
    id: str
    pair: List[str]           # ["PlanetA","AspectName","PlanetB"]
    applies_to: List[str]
    core_meaning: str
    facets: Dict[str, str]
    life_event_type: List[str]
    risk_notes: List[str]
    actionables: Dict[str, List[str]]
    keywords: List[str]
    quality_tags: List[str]
    weights_hint: Dict
    modifiers: Dict
    theme_overlays: List[str]
    refs: List[str]
    provenance: Dict[str, str]
    locales: Dict[str, Dict[str, str]]
    retrieval: Dict[str, Dict[str, str]]

# --- Main card maker -----------------------------------------------------------

LIFE_EVENT_MAP: Dict[Tuple[str, str, str], List[str]] | None = None

def _load_life_event_mapping(path: str = LIFE_EVENTS_CSV) -> Dict[Tuple[str, str, str], List[str]]:
    """Load mapping of (PlanetA, AspectName, PlanetB) -> [Life Event labels].

    CSV expected columns (at least first two used):
      Aspect, Life event, ...
    Aspect column format examples:
      "Jupiter, Conjunction, Sun"
      "Saturn, Square, Ascendant" (will be ignored if planet not in PLANETS list)

    We strip whitespace, require at least 3 comma-separated tokens. Any malformed row is skipped.
    Both forward and reverse (PlanetB, AspectName, PlanetA) keys are stored if not already present
    to maximize hit rate when order differs.
    """
    mapping: Dict[Tuple[str, str, str], List[str]] = {}
    if not os.path.exists(path):
        return mapping  # graceful: no file -> empty mapping
    try:
        with open(path, "r", encoding="utf-8-sig") as f:  # utf-8-sig handles BOM if present
            reader = csv.DictReader(f)
            # Normalize fieldnames in case of capitalization variants
            # Expect 'Aspect' and 'Life event'
            for row in reader:
                aspect_field = row.get("Aspect") or row.get("aspect")
                life_event = (row.get("Life event") or row.get("Life Event") or "").strip()
                if not aspect_field or not life_event:
                    continue
                parts = [p.strip() for p in aspect_field.split(',') if p.strip()]
                if len(parts) < 3:
                    continue
                p1, aspect_name, p2 = parts[0], parts[1], parts[2]
                # Guard: only include if planets recognized (otherwise skip like MC/IC/Ascendant for now)
                if p1 not in PLANETS or p2 not in PLANETS:
                    continue
                key = (p1, aspect_name, p2)
                rev_key = (p2, aspect_name, p1)
                lst = mapping.setdefault(key, [])
                if life_event not in lst:
                    lst.append(life_event)
                # Also add to reverse key list to keep both orders in sync
                rev_lst = mapping.setdefault(rev_key, [])
                if life_event not in rev_lst:
                    rev_lst.append(life_event)
    except Exception:
        # Fail silent to avoid generation crash; mapping stays empty
        return {}
    return mapping

def _life_events_for(p1: str, aspect_name: str, p2: str) -> List[str]:
    global LIFE_EVENT_MAP
    if LIFE_EVENT_MAP is None:
        LIFE_EVENT_MAP = _load_life_event_mapping()
    return LIFE_EVENT_MAP.get((p1, aspect_name, p2), [])

def make_card(p1: str, asp_code: str, p2: str) -> AspectCard:
    asp_name = ASPECTS[asp_code]
    card_id = id_for(p1, asp_code, p2)
    today = str(date.today())

    core = _compose_core(p1, p2, asp_code)
    facets = _compose_facets(p1, p2, asp_code)
    life_event_type = _life_events_for(p1, asp_name, p2)
    actionables = _compose_actionables(p1, p2, asp_code)
    keywords = _keywords(p1, p2, asp_code)
    quality = _aspect_valence_tags(p1, p2, asp_code)
    weights_hint = _weights_hint(p1, p2, asp_code)
    risk_notes = _risk_notes(p1, p2, asp_code)
    locales = _locales(p1, p2, asp_code, core)
    retrieval = _retrieval_blocks(p1, p2, asp_code, core, facets)
    modifiers = _modifiers()

    return AspectCard(
        id=card_id,
        pair=[p1, asp_name, p2],
        applies_to=APPLIES_TO,
        core_meaning=core,
        facets=facets,
        life_event_type=life_event_type,
        risk_notes=risk_notes,
        actionables=actionables,
        keywords=keywords,
        quality_tags=quality,
        weights_hint=weights_hint,
        modifiers=modifiers,
        theme_overlays=[
            # Light auto-tags to help you filter later:
            "Career Advancement" if any(k in keywords for k in ["authority","promotion","structure","growth"]) else "",
            "Relationship Tone" if any(k in keywords for k in ["harmony","bonding","affection","boundaries"]) else "",
            "Wealth & Pricing" if any(k in keywords for k in ["commerce","pricing","abundance","trading"]) else "",
            "Health & Routine" if any(k in keywords for k in ["vitality","routine","inflammation","sleep"]) else ""
        ],
        refs=[],  # e.g., ["Brihat Parashara Hora Shastra ref", "PracticeNotes-17"]
        provenance={"author": "AstroVision Seed+", "reviewed_at": today},
        locales=locales,
        retrieval=retrieval
    )
# -----------------------------
# Generation
# -----------------------------

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

def generate_cards() -> List[AspectCard]:
    cards: List[AspectCard] = []
    for asp_code in ASPECTS.keys():
        for i, a in enumerate(PLANETS):
            for j, b in enumerate(PLANETS):
                if a == b and not INCLUDE_SELF_ASPECTS:
                    continue
                p1, p2 = (a, b)
                if CANONICALIZE_ORDER:
                    p1, p2 = canonical_pair(a, b)
                    # If canonicalization collapsed identical pair but comes from opposite loop order,
                    # we still only want one card per unordered pair for symmetric aspects.
                    # To enforce uniqueness, only accept when (a,b) == canonical; otherwise skip.
                    if (p1, p2) != (a, b):
                        # We skip duplicates produced by reverse order
                        continue
                # If excluding duplicates without canonicalization, you'd add a set check here.

                card = make_card(p1, asp_code, p2)
                cards.append(card)
    return cards

def write_cards(cards: List[AspectCard]) -> None:
    ensure_dirs()
    index = []
    for c in cards:
        # Directory per first three tokens of id can help file systems; here we keep it flat for simplicity
        path = os.path.join(OUTPUT_DIR, f"{c.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(c), f, ensure_ascii=False, indent=2)
        index.append({"id": c.id, "pair": c.pair, "path": path})
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"count": len(index), "items": index}, f, ensure_ascii=False, indent=2)

def main():
    cards = generate_cards()
    write_cards(cards)
    print(f"Generated {len(cards)} cards.")
    print(f"- Cards dir: {os.path.abspath(OUTPUT_DIR)}")
    print(f"- Index:     {os.path.abspath(INDEX_PATH)}")

if __name__ == "__main__":
    # Optional simple CLI toggles via env/args can be added; keeping it minimal.
    try:
        main()
        # test_card = make_card("Jupiter", "CON", "Sun")
        # print(json.dumps(asdict(test_card), indent=2))
    except KeyboardInterrupt:
        sys.exit(1)
