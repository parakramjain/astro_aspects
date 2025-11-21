# --- Vedic-aware mini knowledge base (concise, extensible) --------------------
from typing import Dict
from datetime import date

BENEFICS = {"Venus", "Jupiter", "Mercury", "Moon"}             # classical benefics (Moon waning can be mixed; keep simple)
MALEFICS = {"Mars", "Saturn", "Rahu", "Ketu", "Sun"}           # Sun is a mild malefic in some Vedic contexts

PLANET_ARCH = {
    "Sun": {
        "tags": ["ego", "identity", "authority", "vitality", "purpose", "visibility"],
        "career": "Authority, recognition, leadership, alignment with purpose.",
        "relationships": "Self-respect, healthy boundaries, paternal figures.",
        "money": "Status-linked income, government/authority-linked gains.",
        "health": "Heart, vitality, heat regulation; consider circadian rhythm."
    },
    "Moon": {
        "tags": ["emotion", "care", "habits", "home", "public mood", "mother"],
        "career": "Public reception, brand sentiment, consistency.",
        "relationships": "Bonding, nurturance, emotional safety.",
        "money": "Cyclic cashflow, consumer sentiment.",
        "health": "Hydration, sleep, digestion; stress sensitivity."
    },
    "Mercury": {
        "tags": ["analysis", "communication", "commerce", "learning", "tech"],
        "career": "Negotiation, analytics, documentation, skilling.",
        "relationships": "Dialog, problem-solving, curiosity.",
        "money": "Trading, freelancing, multi-stream income, contracts.",
        "health": "Nervous system, breath, routine mobility."
    },
    "Venus": {
        "tags": ["affection", "art", "harmony", "pleasure", "values"],
        "career": "Design, branding, client harmony, tasteful presentation.",
        "relationships": "Attraction, diplomacy, reciprocity.",
        "money": "Luxury/beauty revenues, pricing power via desirability.",
        "health": "Glucose balance, skin, reproductive health; moderation."
    },
    "Mars": {
        "tags": ["drive", "assertion", "surgery", "mechanics", "conflict"],
        "career": "Execution speed, competition, technical grit.",
        "relationships": "Desire, boundaries, anger management.",
        "money": "Risk-capital, decisive investments, initiative-led gains.",
        "health": "Inflammation, accidents; channel via training."
    },
    "Jupiter": {
        "tags": ["growth", "wisdom", "mentor", "law", "faith", "abundance"],
        "career": "Mentorship, promotions, strategic expansion.",
        "relationships": "Goodwill, generosity, shared purpose.",
        "money": "Scaling revenue, windfalls, ethical growth.",
        "health": "Liver, metabolic balance; avoid excess."
    },
    "Saturn": {
        "tags": ["discipline", "structure", "time", "limits", "dharma via effort"],
        "career": "Authority via mastery, long-term credibility.",
        "relationships": "Commitment realism, boundaries, duty.",
        "money": "Slow steady accrual, austerity, debt realism.",
        "health": "Bones, teeth, chronic load; routines & posture."
    },
    "Rahu": {
        "tags": ["innovation", "foreign", "viral", "obsession", "AI", "media"],
        "career": "Breakthroughs, unconventional paths, visibility spikes.",
        "relationships": "Magnetism with novelty; boundary ambiguity.",
        "money": "Speculative peaks, platform effects, hype cycles.",
        "health": "Anxiety, toxins; digital hygiene, grounding."
    },
    "Ketu": {
        "tags": ["detachment", "past mastery", "subtlety", "surgery", "moksha"],
        "career": "Expert minimalism, silent excellence, niche mastery.",
        "relationships": "Selective intimacy, spiritual bonds.",
        "money": "Decluttering wealth paths; high-skill niches.",
        "health": "Autoimmune, subtle issues; meditation, pranayama."
    },
}

# Aspect codes and pretty names (major first)
ASPECTS: Dict[str, str] = {
    "CON": "Conjunction",
    "OPP": "Opposition",
    "SQR": "Square",
    "TRI": "Trine",
    "SEX": "Sextile",
    # Optional minors—uncomment if you want them generated too
    # "QNC": "Quincunx",
    # "QNT": "Quintile",
    # "SSX": "Semi-Sextile",
    # "SSQ": "Semi-Square",
    # "SES": "Sesquiquadrate",
    # "PAR": "Parallel",
    # "CPA": "Contra-Parallel",
}

# Aspect semantics (western names kept; add your own codes to ASPECTS)
ASPECT_SEM = {
    "CON": {"name": "Conjunction", "tone": "intensification", "valence": "mixed"},
    "OPP": {"name": "Opposition",  "tone": "polarity/awareness", "valence": "mixed"},
    "SQR": {"name": "Square",      "tone": "friction/work", "valence": "challenging"},
    "TRI": {"name": "Trine",       "tone": "ease/flow", "valence": "benefic"},
    "SEX": {"name": "Sextile",     "tone": "opportunity/skill", "valence": "benefic"},
    # Feel free to extend (quincunx, quintile, etc.)
}

# Action templates per phase (auto-tailored below with planet verbs)
PHASE_ACTIONS = {
    "applying": [
        "Prepare and initiate aligned actions; set intent and book resources.",
        "Skill-up or pre-negotiate; clear blockers proactively."
    ],
    "exact": [
        "Announce, pitch, launch, or sign; maximize visibility.",
        "Make the decisive call; accept/decline offers consciously."
    ],
    "separating": [
        "Consolidate gains, document learnings, adjust guardrails.",
        "Close loops, stabilize routines, prune scope creep."
    ]
}

# Simple dignity/retrograde scaffolding (expand with your chart engine)
DIGNITY_HINTS = {
    "Sun": {"exalt": "Aries", "detriment": "Aquarius", "debilitation": "Libra"},
    "Moon": {"exalt": "Taurus", "debilitation": "Scorpio"},
    "Mars": {"exalt": "Capricorn", "detriment": "Cancer"},
    "Mercury": {"exalt": "Virgo", "detriment": "Pisces"},
    "Jupiter": {"exalt": "Cancer", "debilitation": "Capricorn"},
    "Venus": {"exalt": "Pisces", "debilitation": "Virgo"},
    "Saturn": {"exalt": "Libra", "detriment": "Cancer"},
    "Rahu": {}, "Ketu": {}
}

# Default weights and orbs used by helper functions (safe sensible defaults)
DEFAULT_ORB_DEG = {
    "CON": 1.5,
    "OPP": 3,
    "SQR": 3,
    "TRI": 6,
    "SEX": 4
}

PLANET_WEIGHT = {
    "Sun": 1.0,
    "Moon": 0.9,
    "Mercury": 0.85,
    "Venus": 0.9,
    "Mars": 0.8,
    "Jupiter": 0.95,
    "Saturn": 0.85,
    "Rahu": 0.8,
    "Ketu": 0.8
}

CLASS_WEIGHT = {
    "benefic": 1.0,
    "challenging": 0.8,
    "mixed": 0.9
}

# --- Helper composers ----------------------------------------------------------

def _aspect_valence_tags(p1: str, p2: str, asp_code: str):
    tags = ["major" if asp_code in {"CON","OPP","SQR","TRI","SEX"} else "minor"]
    a = ASPECT_SEM.get(asp_code, {"valence": "mixed"})["valence"]
    if a == "benefic":
        tags.append("benefic")
    elif a == "challenging":
        tags.append("challenging")
    else:
        tags.append("mixed")

    # Planet synergy tweaks
    benefic_count = sum([p in BENEFICS for p in (p1, p2)])
    malefic_count = sum([p in MALEFICS for p in (p1, p2)])
    if benefic_count == 2 and asp_code in {"TRI","SEX"}:
        tags.append("external-opportunity")
    if malefic_count >= 1 and asp_code in {"SQR","OPP"}:
        tags.append("discipline-required")
    if asp_code == "CON":
        tags.append("fusion")

    return list(dict.fromkeys(tags))  # dedupe, preserve order


def _verb_bridge(asp_code: str):
    tone = ASPECT_SEM.get(asp_code, {}).get("tone", "interaction")
    if asp_code == "CON": return f"fuses in {tone}"
    if asp_code == "OPP": return f"faces {tone}"
    if asp_code == "SQR": return f"drives {tone}"
    if asp_code == "TRI": return f"flows with {tone}"
    if asp_code == "SEX": return f"opens {tone}"
    return f"interacts via {tone}"


def _compose_core(p1: str, p2: str, asp_code: str):
    a = ASPECT_SEM.get(asp_code, {"name": "Aspect", "tone": "interaction"})
    b = _verb_bridge(asp_code)
    p1_tags = ", ".join(PLANET_ARCH.get(p1, {}).get("tags", []))
    p2_tags = ", ".join(PLANET_ARCH.get(p2, {}).get("tags", []))
    lines = [
        f"{a['name']} between {p1} and {p2} {b}.",
        f"{p1}: {p1_tags}. {p2}: {p2_tags}.",
    ]
    # Valence short
    val = a.get("valence", "mixed")
    if val == "benefic":
        lines.append("General tenor: supportive, opportunity-rich; progress with modest effort.")
    elif val == "challenging":
        lines.append("General tenor: growth via friction; endurance and clear boundaries are key.")
    else:
        lines.append("General tenor: mixed; outcome depends on maturity, timing, and context.")
    return " ".join([s for s in lines if s])


def _facet_sentence(planet: str, domain: str):
    if domain == "career": return PLANET_ARCH.get(planet, {}).get("career", "")
    if domain == "relationships": return PLANET_ARCH.get(planet, {}).get("relationships", "")
    if domain == "money": return PLANET_ARCH.get(planet, {}).get("money", "")
    if domain == "health_adj": return PLANET_ARCH.get(planet, {}).get("health", "")
    return ""


def _compose_facets(p1: str, p2: str, asp_code: str):
    # Blend both planets with aspect tone
    tone = ASPECT_SEM.get(asp_code, {}).get("tone", "interaction")
    def blend(domain):
        s1 = _facet_sentence(p1, domain)
        s2 = _facet_sentence(p2, domain)
        if not (s1 or s2): return f"Influence emerges via {tone}."
        return f"{s1} {(' ' if s1 and s2 else '')}{s2} Emphasis: {tone}."
    return {
        "career": blend("career"),
        "relationships": blend("relationships"),
        "money": blend("money"),
        "health_adj": blend("health_adj")
    }


def _compose_actionables(p1: str, p2: str, asp_code: str):
    # Tailor some verbs from planets
    verbs = {
        "Mercury": "draft, analyze, negotiate",
        "Venus": "design, harmonize, price",
        "Mars": "execute, train, assert",
        "Jupiter": "mentor, expand, publish",
        "Saturn": "structure, commit, audit",
        "Sun": "lead, present, decide",
        "Moon": "nurture, align routines, soft-launch",
        "Rahu": "experiment, market, amplify",
        "Ketu": "refine, specialize, simplify"
    }
    pv = lambda p: verbs.get(p, "act, iterate, measure")

    def tailor(base_list):
        # add planet verbs and aspect tone
        tone = ASPECT_SEM.get(asp_code, {}).get("tone", "interaction")
        extra = f" ({p1}: {pv(p1)}; {p2}: {pv(p2)}; tone: {tone})."
        return [s + extra for s in base_list]

    return {
        "applying": tailor(PHASE_ACTIONS["applying"]),
        "exact": tailor(PHASE_ACTIONS["exact"]),
        "separating": tailor(PHASE_ACTIONS["separating"])
    }


def _keywords(p1: str, p2: str, asp_code: str):
    tags = set()
    tags.update(PLANET_ARCH.get(p1, {}).get("tags", []))
    tags.update(PLANET_ARCH.get(p2, {}).get("tags", []))
    tags.update(ASPECT_SEM.get(asp_code, {}).get("tone", "interaction").split("/"))
    tags.update([ASPECT_SEM.get(asp_code, {}).get("name", "").lower()])
    return sorted(tags)


def _weights_hint(p1: str, p2: str, asp_code: str):
    return {
        "default_orb_deg": DEFAULT_ORB_DEG.get(asp_code, 3),
        "planet_weight": {
            p1: PLANET_WEIGHT.get(p1, 0.8),
            p2: PLANET_WEIGHT.get(p2, 0.8)
        },
        "class_weight": CLASS_WEIGHT
    }


def _risk_notes(p1: str, p2: str, asp_code: str):
    risks = []
    val = ASPECT_SEM.get(asp_code, {}).get("valence", "mixed")
    if val == "benefic":
        risks.append("Complacency or overextension; assuming goodwill covers weak execution.")
    if val in {"challenging", "mixed"}:
        risks.append("Friction escalating into conflict; respect pacing and boundaries.")
    if "Rahu" in {p1, p2}:
        risks.append("Hype or obsession; verify sources and detox from overexposure.")
    if "Ketu" in {p1, p2}:
        risks.append("Detachment causing under-communication; document commitments.")
    if "Saturn" in {p1, p2}:
        risks.append("Burnout via over-responsibility; schedule recovery windows.")
    if "Mars" in {p1, p2}:
        risks.append("Impulsive actions or accidents; channel energy into training.")
    if "Jupiter" in {p1, p2}:
        risks.append("Overpromising; align scale with capacity.")
    if "Venus" in {p1, p2}:
        risks.append("People-pleasing → scope creep; set clear give-and-get.")
    return risks


def _locales(p1: str, p2: str, asp_code: str, core_en: str):
    asp_name = ASPECTS[asp_code]
    # Super-concise Hindi summary builder (keep simple and friendly)
    core_hi = (
        f"{p1} और {p2} का {asp_name} — ऊर्जा {ASPECT_SEM.get(asp_code, {}).get('tone','मेल-जोल')} के रूप में चलती है. "
        f"थोड़ा संतुलन रखें; अवसर और सीख दोनों मिलेंगे."
    )
    return {
        "en": {
            "title": f"{p1} {asp_name} {p2}",
            "core": core_en,
            "tone": "warm"
        },
        "hi": {
            "title": f"{p1} {asp_name} {p2} (हिन्दी)",
            "core": core_hi,
            "tone": "सरल"
        }
    }


def _retrieval_blocks(p1: str, p2: str, asp_code: str, core_en: str, facets: dict):
    asp_name = ASPECTS[asp_code]
    return {
        "embedding_sections": {
            "core": core_en,
            "career": facets["career"],
            "relationships": facets["relationships"],
            "money": facets["money"],
            "health_adj": facets["health_adj"]
        },
        "aliases": [
            f"{p1} {asp_name.lower()} {p2}",
            f"{p1[:3]} {asp_code} {p2[:3]}",
            f"{p1}-{asp_name}-{p2}",
            f"{p1} {asp_name} to {p2}"
        ]
    }


def _modifiers():
    # Leave hooks for your engine to inject real-time dignity/retrograde adjustments
    return {
        "dignity_adjustment": {
            "notes": "Optional: adjust weights by sign/hse dignity e.g., exalt/debilitation.",
            "rules_hint": DIGNITY_HINTS
        },
        "retrograde_adjustment": {
            "notes": "Optional: if either planet retrograde, temper extroversion; increase review loops."
        }
    }
