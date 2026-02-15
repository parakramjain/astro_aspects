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
import json, os, sys, re
import difflib
from dataclasses import dataclass, asdict
import csv
from datetime import date
from typing import Dict, List, Tuple, Any, Optional, cast
# import all the functions and variables from vedic_kb.py
from vedic_kb import *
from vedic_kb import _compose_core, _compose_facets, _compose_actionables, _keywords, _aspect_valence_tags, _weights_hint, _risk_notes, _locales, _retrieval_blocks, _modifiers
import pandas as pd

try:
    # Optional dependency; required only for GPT-backed rebuild
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # lazy import guard; validated at runtime when GPT is used

# -----------------------------
# Config — tweak as you like
# -----------------------------
# Note: Use OPENAI_API_KEY (or Azure equivalents) from environment; do not hardcode secrets in source.
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

# -----------------------------
# Excel → GPT bilingual rebuild
# -----------------------------

# Accepted aspect names → codes (robust to common variants)
_ASPECT_CODE_BY_NAME = {
    "conjunction": "CON",
    "opp": "OPP", "opposition": "OPP",
    "sqr": "SQR", "square": "SQR",
    "tri": "TRI", "trine": "TRI",
    "sxt": "SXT", "sextile": "SXT",  # sextile code
}

def _to_planet_code(name: str) -> str:
    return name.strip()[:3].upper()

def _normalize_aspect_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())

def id_from_astro_aspect(astro_aspect: str, version: str = VERSION) -> Tuple[Optional[str], Optional[str]]:
    """Map 'Jupiter Conjunction Moon' → ('JUP_CON_MOO__v1.0.0', None).

    Returns (None, reason) if parsing fails. Attempts typo-tolerant normalization for
    planet names and aspect names; flags unsupported planets explicitly.
    """
    if not astro_aspect:
        return None, "Empty Astro_Aspect"

    def _norm_planet(tok: str) -> Tuple[Optional[str], Optional[str]]:
        raw = tok.strip().lower()
        # quick synonyms/typos
        synonyms = {
            "jupyter": "Jupiter",
            "mercury": "Mercury",
            "venus": "Venus",
            "mars": "Mars",
            "jupiter": "Jupiter",
            "saturn": "Saturn",
            "uranus": "Uranus",
            "neptune": "Neptune",
            "pluto": "Pluto",
            "sun": "Sun",
            "moon": "Moon",
            # common nodes if present in data
            "rahu": "Rahu",
            "ketu": "Ketu",
        }
        if raw in synonyms:
            canon = synonyms[raw]
        else:
            # fuzzy match against all known labels
            candidates = [p.lower() for p in PLANETS] + ["rahu", "ketu"]
            match = difflib.get_close_matches(raw, candidates, n=1, cutoff=0.75)
            if not match:
                return None, f"Unknown planet token '{tok}'"
            m = match[0]
            canon = m.capitalize() if m in {"sun","moon","mars"} else m.title()
            # normalize to canonical casing
            if canon.lower() == "uranus": canon = "Uranus"
            if canon.lower() == "neptune": canon = "Neptune"
        if canon not in PLANETS:
            return None, f"Unsupported planet '{canon}' (not in project PLANETS)"
        return canon, None

    def _norm_aspect(tok: str) -> Tuple[Optional[str], Optional[str]]:
        raw = tok.strip().lower()
        name_variants = {
            "conjunction": "CON",
            "conjuction": "CON",
            "conj": "CON",
            "opposition": "OPP",
            "opp": "OPP",
            "square": "SQR",
            "sqr": "SQR",
            "trine": "TRI",
            "tri": "TRI",
            "sextile": "SXT",
            "sext": "SXT",
            "sxt": "SXT",
            "sex": "SXT",
        }
        if raw in name_variants:
            return name_variants[raw], None
        # fuzzy against keys
        keys = list(name_variants.keys())
        match = difflib.get_close_matches(raw, keys, n=1, cutoff=0.7)
        if match:
            return name_variants[match[0]], None
        # accept direct codes too
        if raw.upper() in {"CON","OPP","SQR","TRI","SXT"}:
            return raw.upper(), None
        return None, f"Unknown aspect token '{tok}'"

    s = _normalize_aspect_name(astro_aspect)
    parts = s.split(" ")
    if len(parts) < 3:
        return None, "Expected format 'Planet Aspect Planet'"

    p1_raw = parts[0]
    asp_raw = parts[1]
    p2_raw = " ".join(parts[2:])

    p1, e1 = _norm_planet(p1_raw)
    if e1:
        return None, e1
    asp_code, e2 = _norm_aspect(asp_raw)
    if e2:
        return None, e2
    p2, e3 = _norm_planet(p2_raw)
    if e3:
        return None, e3

    return f"{_to_planet_code(cast(str, p1))}_{asp_code}_{_to_planet_code(cast(str, p2))}__{version}", None


def _gpt_client_or_raise() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Please add 'openai>=1.40.0' to requirements.txt.")
    # Uses environment variables for API key (OPENAI_API_KEY or Azure config)
    return OpenAI()


def _build_bilingual_schema_prompt() -> str:
    return (
        f"""You are an expert Vedic astrologer-editor and bilingual (English + Hindi) content specialist.

            You will receive two inputs:
            1. An English description of an astrological aspect.
            2. A Hindi Unicode description of the same aspect.

            Your task is to derive ALL output strictly, logically, and conservatively from these descriptions only.
            Do NOT introduce new rules, doctrines, predictions, medical statements, financial promises, or unsupported claims.

            Guidelines:
            - Stay concise, specific, and production-grade.  
            - Maintain a warm, neutral, non-deterministic tone.  
            - English must be clear and natural; Hindi must be simple, natural Unicode Hindi.  
            - Keep astrological interpretation grounded in the given text—no external astrology knowledge unless clearly implied.
            - Avoid fatalism or deterministic outcomes; avoid interpreting beyond the scope of the descriptions.
            - If descriptions are vague, reflect uncertainty gently and stay within textual boundaries.
            - Output must match the exact JSON schema given. No extra fields, no missing fields, no reordering, no commentary.

            Your role: Extract patterns → structure them → provide high-quality bilingual content strictly from the source material.
            """
    )


def _bilingual_json_schema() -> Dict[str, Any]:
    """Return a JSON schema that enforces bilingual fields for semantic content."""
    return {
        "name": "aspect_card_bilingual_update",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "core_meaning", "facets", "life_event_type", "risk_notes",
                "actionables", "keywords", "quality_tags", "theme_overlays",
                "locales", "retrieval"
            ],
            "properties": {
                # Text properties (bilingual strings)
                "core_meaning": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}
                },
                # Facets: domain objects each bilingual {en, hi}
                "facets": {
                    "type": "object",
                    "required": ["career", "relationships", "money", "health_adj"],
                    "properties": {
                        "career": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                        "relationships": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                        "money": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                        "health_adj": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}}
                    }
                },
                # Lists bilingual
                "life_event_type": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}
                },
                "risk_notes": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}
                },
                # Actionables: phases each bilingual
                "actionables": {
                    "type": "object",
                    "required": ["applying", "exact", "separating"],
                    "properties": {
                        "applying": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}},
                        "exact": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}},
                        "separating": {"type": "object", "required": ["en", "hi"], "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}}
                    }
                },
                "keywords": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}
                },
                "quality_tags": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}
                },
                "theme_overlays": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {"en": {"type": "array", "items": {"type": "string"}}, "hi": {"type": "array", "items": {"type": "string"}}}
                },
                # locales remains bilingual title/core/tone
                "locales": {
                    "type": "object",
                    "required": ["en", "hi"],
                    "properties": {
                        "en": {"type": "object", "required": ["title", "core", "tone"], "properties": {"title": {"type": "string"}, "core": {"type": "string"}, "tone": {"type": "string"}}},
                        "hi": {"type": "object", "required": ["title", "core", "tone"], "properties": {"title": {"type": "string"}, "core": {"type": "string"}, "tone": {"type": "string"}}}
                    }
                },
                # retrieval embedding sections: per-section bilingual strings
                "retrieval": {
                    "type": "object",
                    "required": ["embedding_sections"],
                    "properties": {
                        "embedding_sections": {
                            "type": "object",
                            "required": ["core","career","relationships","money","health_adj"],
                            "properties": {
                                "core": {"type": "object", "required": ["en","hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                                "career": {"type": "object", "required": ["en","hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                                "relationships": {"type": "object", "required": ["en","hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                                "money": {"type": "object", "required": ["en","hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}},
                                "health_adj": {"type": "object", "required": ["en","hi"], "properties": {"en": {"type": "string"}, "hi": {"type": "string"}}}
                            }
                        }
                    }
                }
            }
        }
    }


def _call_gpt_bilingual(
    client: Any,
    english_desc: str,
    hindi_desc: str,
    full_aspect: str,
    astro_aspect: str,
    seed_keywords: Optional[List[str]] = None,
    model: str = "gpt-4.1",
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Call GPT to create the bilingual structured content from given descriptions.

    The model must derive content only from the descriptions; no external rules.
    """
    system_prompt = _build_bilingual_schema_prompt()
    schema = _bilingual_json_schema()
    seed_keywords = seed_keywords or []

    user_prompt = (
        f"Full Aspect: {full_aspect}\n"
        f"Astro_Aspect (canonical): {astro_aspect}\n\n"
        f"English Description:\n{english_desc}\n\n"
        f"Hindi Description (Unicode):\n{hindi_desc}\n\n"
        f"""
        Instructions:

        Using ONLY the English and Hindi descriptions provided above:
        - Derive the bilingual content for ALL required fields:
        core meaning, facets, life-event type, risk notes, actionables (applying/exact/separating), 
        keywords, quality tags, theme overlays, and tone.
        - All content must directly reflect themes, emotions, behaviours, opportunities, and cautions 
        present or clearly implied in the descriptions.
        - Avoid doctrinal, fatalistic, or invented astrological statements. Keep interpretations text-based.
        - Keywords, quality tags, and themes should be extracted from the descriptions—not invented.
        - Write Hindi and English versions that are parallel in meaning but naturally phrased in each language.
        - If English and Hindi descriptions conflict, favor the English description while acknowledging uncertainty lightly.
        - If Hindi text lacks clarity, infer meaning conservatively from the English version.
        - If a field naturally needs bullet points, produce short, crisp bullets—no long paragraphs.
        - Use a professional tone suitable for a production astrology application.

        Output Requirements:
        - The output MUST strictly conform to the provided bilingual JSON schema.
        - No additional text outside the JSON.  
        - No commentary, reasoning, or explanation.  
        - Ensure both `en` and `hi` keys are fully populated for all bilingual fields.

        Optional:
        - Use seed keywords (if provided) only if they match the meaning of the descriptions: {seed_keywords}.\n
        """
    )

    # Try with json_schema response formatting when supported; fallback to prompt-embedded schema
    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": schema,
            },
        )
    except TypeError:
        # Older SDKs: no response_format support. Embed schema in the content and request raw JSON.
        prompt_with_schema = (
            user_prompt
            + "\nYou must output a single JSON object matching this JSON Schema strictly (no extra commentary):\n"
            + json.dumps(schema)
        )
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_with_schema},
            ],
            temperature=temperature,
        )

    # Best-effort extraction of the textual JSON from the SDK response (varies by version)
    content_text: Optional[str] = None
    try:
        out0 = getattr(resp, "output", [None])[0]
        if out0 is not None:
            content = getattr(out0, "content", None) or (out0.get("content") if isinstance(out0, dict) else None)
            if content:
                for c in content:
                    txt = getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else None)
                    if txt:
                        content_text = txt
                        break
        if not content_text:
            content_text = getattr(out0, "text", None) or (out0.get("text") if isinstance(out0, dict) else None)
    except Exception:
        content_text = None
    if content_text is None:
        if isinstance(resp, str):
            content_text = resp
        elif isinstance(resp, dict):
            content_text = resp.get("text") or resp.get("output")

    if not content_text:
        raise RuntimeError("Failed to parse GPT response text for bilingual content.")

    try:
        return json.loads(content_text)
    except Exception as e:
        # surface the raw for debugging if JSON parsing fails
        raise RuntimeError(f"GPT returned non-JSON or invalid JSON: {e}\n{content_text[:3000]}")


def _call_gpt_bilingual_chat_fallback(
    client: Any,
    english_desc: str,
    hindi_desc: str,
    full_aspect: str,
    astro_aspect: str,
    seed_keywords: Optional[List[str]] = None,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Secondary fallback using Chat Completions API to coerce JSON output."""
    system_prompt = _build_bilingual_schema_prompt()
    schema = _bilingual_json_schema()
    seed_keywords = seed_keywords or []

    user_prompt = (
        f"Full Aspect: {full_aspect}\n"
        f"Astro_Aspect (canonical): {astro_aspect}\n\n"
        f"English Description:\n{english_desc}\n\n"
        f"Hindi Description (Unicode):\n{hindi_desc}\n\n"
        "Instructions:\n"
        "- Infer core meaning, facets, risks, actionables, keywords, tones, quality tags, and theme overlays strictly from the above descriptions.\n"
        "- Keep terms clear and consistent; avoid doctrinal assertions not present in the text.\n"
        "- Output MUST be a single JSON object matching the provided JSON schema. No extra text.\n"
        f"- If domain bullets conflict, prefer English description; reflect uncertainty gently. Seed keywords (optional): {seed_keywords}.\n"
        "\nJSON Schema (repeat):\n" + json.dumps(schema)
    )

    try:
        chat = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
    except TypeError:
        # very old SDKs: no response_format; still ask firmly for JSON-only
        chat = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\nReturn only the JSON, no commentary."},
            ],
            temperature=temperature,
        )

    text = None
    try:
        text = chat.choices[0].message.content
    except Exception:
        pass
    if not text:
        raise RuntimeError("Chat completion returned empty content.")
    try:
        return json.loads(text)
    except Exception as e:
        raise RuntimeError(f"Chat completion JSON parse failed: {e}\n{text[:3000]}")


def _bilingual_theme_overlays_from_keywords(keywords_en: List[str]) -> List[str]:
    """Tiny heuristic to keep overlays in a familiar set; used when GPT omits them."""
    overlays = []
    kw = set([k.lower() for k in keywords_en])
    if {"career", "promotion", "leadership", "recognition", "authority"} & kw:
        overlays.append("Career Advancement")
    if {"relationship", "harmony", "bonding", "affection", "boundaries"} & kw:
        overlays.append("Relationship Tone")
    if {"wealth", "pricing", "abundance", "trading", "money", "revenue"} & kw:
        overlays.append("Wealth & Pricing")
    if {"health", "vitality", "routine", "sleep", "inflammation"} & kw:
        overlays.append("Health & Routine")
    return overlays or ["Career Advancement", "Relationship Tone", "Wealth & Pricing", "Health & Routine"]


def _validate_bilingual_payload(gen: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    required_top = [
        "core_meaning", "facets", "life_event_type", "risk_notes",
        "actionables", "keywords", "quality_tags", "locales", "retrieval"
    ]
    for k in required_top:
        if k not in gen:
            return False, f"Missing top-level field: {k}"
    # Spot-check bilingual structure for a few keys
    # core_meaning: bilingual
    cm = gen.get("core_meaning")
    if not (isinstance(cm, dict) and "en" in cm and "hi" in cm):
        return False, "Field 'core_meaning' must be object with 'en' and 'hi'"
    # facets: domains each bilingual
    facets = gen.get("facets")
    if not isinstance(facets, dict):
        return False, "Field 'facets' must be object"
    for dom in ["career","relationships","money","health_adj"]:
        d = facets.get(dom)
        if not (isinstance(d, dict) and "en" in d and "hi" in d):
            return False, f"facets.{dom} must be object with 'en' and 'hi'"
    # life_event_type, risk_notes, keywords, quality_tags: bilingual arrays
    for k in ["life_event_type","risk_notes","keywords","quality_tags","theme_overlays"]:
        v = gen.get(k)
        if not (isinstance(v, dict) and "en" in v and "hi" in v):
            return False, f"Field '{k}' must be object with 'en' and 'hi'"
    # actionables: phases each bilingual list
    act = gen.get("actionables")
    if not isinstance(act, dict):
        return False, "Field 'actionables' must be object"
    for ph in ["applying","exact","separating"]:
        p = act.get(ph)
        if not (isinstance(p, dict) and "en" in p and "hi" in p):
            return False, f"actionables.{ph} must be object with 'en' and 'hi'"
    # locales: bilingual
    loc = gen.get("locales")
    if not (isinstance(loc, dict) and "en" in loc and "hi" in loc):
        return False, "Field 'locales' must be object with 'en' and 'hi'"
    # retrieval.embedding_sections: per-section bilingual
    emb = gen.get("retrieval", {}).get("embedding_sections")
    if not isinstance(emb, dict):
        return False, "retrieval.embedding_sections must be an object"
    for sec in ["core","career","relationships","money","health_adj"]:
        s = emb.get(sec)
        if not (isinstance(s, dict) and "en" in s and "hi" in s):
            return False, f"retrieval.embedding_sections.{sec} must be object with 'en' and 'hi'"
    return True, None


def rebuild_from_excel_with_gpt(
    excel_path: str,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.3,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Read Excel and update existing aspect card JSONs with bilingual GPT expansions.

    Required columns in Excel:
      - Full Aspect
      - Astro_Aspect
      - Description_English
      - Description_Hindi_Unicode

    Returns a summary dict with counts and any errors.
    """
    df = pd.read_excel(excel_path)
    required_cols = [
        "Full Aspect",
        "Astro_Aspect",
        "Description_English",
        "Description_Hindi_Unicode",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Excel missing required column: {col}")

    client = _gpt_client_or_raise()

    updated, missing, errors = 0, 0, []
    rows = df.to_dict(orient="records")
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    count = 0
    for row in rows:
        full_aspect = str(row.get("Full Aspect", "")).strip()
        astro_aspect = str(row.get("Astro_Aspect", "")).strip()
        desc_en = str(row.get("Description_English", "")).strip()
        desc_hi = str(row.get("Description_Hindi_Unicode", "")).strip()

        card_id, parse_err = id_from_astro_aspect(astro_aspect)
        if not card_id:
            errors.append({"astro_aspect": astro_aspect, "error": parse_err or "Unable to parse Astro_Aspect"})
            continue
        count += 1
        print(f"Processing card #{count}:", card_id)
        path = os.path.join(OUTPUT_DIR, f"{card_id}.json")
        if not os.path.exists(path):
            missing += 1
            continue

        try:
            # Generate bilingual content using GPT
            gen = _call_gpt_bilingual(
                client=client,
                english_desc=desc_en,
                hindi_desc=desc_hi,
                full_aspect=full_aspect,
                astro_aspect=astro_aspect,
                seed_keywords=[],
                model=model,
                temperature=temperature,
            )
        except Exception as e1:
            # Try chat.completions fallback once
            try:
                gen = _call_gpt_bilingual_chat_fallback(
                    client=client,
                    english_desc=desc_en,
                    hindi_desc=desc_hi,
                    full_aspect=full_aspect,
                    astro_aspect=astro_aspect,
                    seed_keywords=[],
                    model=model,
                    temperature=temperature,
                )
            except Exception as e2:
                errors.append({"card_id": card_id, "error": f"GPT error: {str(e1)} | Fallback: {str(e2)}"})
                continue

        # Load current card, merge/replace semantic sections with bilingual structures
        try:
            with open(path, "r", encoding="utf-8") as f:
                cur = json.load(f)
        except Exception as e:
            errors.append({"card_id": card_id, "error": f"Failed reading JSON: {e}"})
            continue
        
        # print("gen:", gen)
        # gen = gen.get("schema", {})
        ok, why = _validate_bilingual_payload(gen)
        if not ok:
            errors.append({"card_id": card_id, "error": f"GPT payload invalid: {why}"})
            continue

        # Update locales (keep title from Excel if available)
        locales_payload = gen.get("locales", {})
        if full_aspect:
            # Overwrite titles with definitive Excel title
            if "en" in locales_payload:
                locales_payload["en"]["title"] = full_aspect
            if "hi" in locales_payload:
                # If Hindi title absent, mirror English title or a transliteration hint
                locales_payload["hi"]["title"] = locales_payload["hi"].get("title") or f"{full_aspect} (हिन्दी)"

        # If GPT missed overlays, synthesize from keywords.en
        overlays = gen.get("theme_overlays") or {}
        if isinstance(overlays, dict):
            en_over = overlays.get("en", []) or []
            if not en_over:
                en_keys = gen.get("keywords", {}).get("en", []) if isinstance(gen.get("keywords"), dict) else []
                overlays["en"] = _bilingual_theme_overlays_from_keywords(en_keys)
            if not overlays.get("hi"):
                # naive copy for HI if GPT omitted; better than empty
                overlays["hi"] = overlays.get("en", [])
            gen["theme_overlays"] = overlays

        # Apply updates
        cur["core_meaning"] = gen["core_meaning"]
        cur["facets"] = gen["facets"]
        # life_event_type: keep also original English-only list for backward compatibility if it exists
        cur["life_event_type"] = gen["life_event_type"]
        cur["risk_notes"] = gen["risk_notes"]
        cur["actionables"] = gen["actionables"]
        cur["keywords"] = gen["keywords"]
        cur["quality_tags"] = gen["quality_tags"]
        cur["theme_overlays"] = gen.get("theme_overlays", cur.get("theme_overlays", {}))
        cur.setdefault("provenance", {})
        cur["provenance"]["reviewed_at"] = str(date.today())
        cur["locales"] = locales_payload
        # retrieval embedding sections — switch to bilingual arrays as required
        cur.setdefault("retrieval", {})
        cur["retrieval"]["embedding_sections"] = gen.get("retrieval", {}).get("embedding_sections", {})

        if dry_run:
            updated += 1
            continue

        # Write back
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cur, f, ensure_ascii=False, indent=2)
            updated += 1
        except Exception as e:
            errors.append({"card_id": card_id, "error": f"Failed writing JSON: {e}"})

    return {"updated": updated, "missing": missing, "errors": errors}

def main():
    # python .\aspect_card_utils\aspect_card_creation.py update-from-excel --excel "C:\Users\parak\Documents\Parakram\astro_project\astro_aspects\aspect_card_utils\main_aspect_data_description_converted_both_filtered.xlsx" --limit 1 --dry-run

    import argparse
    parser = argparse.ArgumentParser(description="Aspect Cards generator and bilingual updater")
    sub = parser.add_subparsers(dest="cmd")

    gen_p = sub.add_parser("generate", help="Generate all aspect cards from templates (no GPT)")

    upd_p = sub.add_parser("update-from-excel", help="Update existing cards from Excel using GPT bilingual expansions")
    upd_p.add_argument("--excel", required=True, help="Path to Excel file with required columns")
    upd_p.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name")
    upd_p.add_argument("--temperature", type=float, default=0.3)
    upd_p.add_argument("--limit", type=int, default=None, help="Max rows to process")
    upd_p.add_argument("--dry-run", action="store_true", help="Do not write files; just simulate")

    args = parser.parse_args()
    if args.cmd == "update-from-excel":
        summary = rebuild_from_excel_with_gpt(
            excel_path=args.excel,
            model=args.model,
            temperature=args.temperature,
            limit=args.limit,
            dry_run=args.dry_run,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    # default: generate all if no subcommand provided
    cards = generate_cards()
    write_cards(cards)
    print(f"Generated {len(cards)} cards.")
    print(f"- Cards dir: {os.path.abspath(OUTPUT_DIR)}")
    print(f"- Index:     {os.path.abspath(INDEX_PATH)}")

if __name__ == "__main__":
    # Optional simple CLI toggles via env/args can be added; keeping it minimal.
    """
    python .\aspect_card_utils\aspect_card_creation.py update-from-excel --excel "C:\Users\parak\Documents\Parakram\astro_project\astro_aspects\aspect_card_utils\main_aspect_data_description_converted_both_filtered.xlsx" --limit 1 --dry-run

    """
    try:
        main()
        # test_card = make_card("Jupiter", "CON", "Sun")
        # print(json.dumps(asdict(test_card), indent=2))
    except KeyboardInterrupt:
        sys.exit(1)
