# aspect_report.py
from __future__ import annotations
import json, os
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import date, datetime

# ---------- Config ----------
KB_DIR = "./kb"
ASPECTS_DIR = os.path.join(KB_DIR, "aspects")
INDEX_PATH = os.path.join(KB_DIR, "index.json")

# Planet canonical names (outer -> inner for canonicalization in your KB)
PLANET_ORDER = ["Pluto","Neptune","Uranus","Saturn","Jupiter","Mars","Venus","Mercury","Moon","Sun"]
PLANET_RANK = {p:i for i,p in enumerate(PLANET_ORDER)}

# Short token normalization (expand as needed)
PLANET_MAP = {
    "Sun":"Sun","Moo":"Moon","Mer":"Mercury","Ven":"Venus","Mar":"Mars",
    "Jup":"Jupiter","Sat":"Saturn","Ura":"Uranus","Nep":"Neptune","Plu":"Pluto",
    "Node":"Node","Nod":"Node"
}
ASPECT_MAP = {
    "Con":"Conjunction","Opp":"Opposition","Tri":"Trine","Sxt":"Sextile","Sex":"Sextile",
    "Squ":"Square","Sqr":"Square","Qnc":"Quincunx","Qnt":"Quintile"
}

# ---------- Data carriers ----------
@dataclass
class AspectWindow:
    start: str
    end: str
    exact: str
    pair: Tuple[str,str,str]  # ("Jupiter","Sextile","Moon")
    raw: Dict[str,Any]        # original row for reference

# ---------- KB loading ----------
def load_index(index_path: str = INDEX_PATH) -> Dict[str, Any]:
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"index.json not found at {index_path}")
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Build a lookup by (P1, AspectName, P2) → card_id
    by_triplet: Dict[Tuple[str,str,str], str] = {}
    id_to_path: Dict[str,str] = {}
    for item in data.get("items", []):
        cid = item["id"]
        pair = item.get("pair") or []
        id_to_path[cid] = item.get("path") or os.path.join(ASPECTS_DIR, f"{cid}.json")
        if len(pair) == 3:
            by_triplet[(pair[0], pair[1], pair[2])] = cid
    return {"by_triplet": by_triplet, "id_to_path": id_to_path, "raw": data}

def load_card(card_id: str, id_to_path: Dict[str,str]) -> Dict[str,Any]:
    path = id_to_path.get(card_id) or os.path.join(ASPECTS_DIR, f"{card_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Card file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- Normalization helpers ----------
def normalize_aspect_tuple(t: Tuple[str,str,str]) -> Tuple[str,str,str]:
    a, asp, b = t
    A = PLANET_MAP.get(a, a).title()
    B = PLANET_MAP.get(b, b).title()
    ASP = ASPECT_MAP.get(asp, asp).title()
    return (A, ASP, B)

def canonicalize_order(a: str, aspect_name: str, b: str) -> Tuple[str,str]:
    # Match your generator’s “outer → inner” order for symmetric aspects
    ra, rb = PLANET_RANK.get(a, 99), PLANET_RANK.get(b, 99)
    if ra < rb:  # a is more outer
        return a, b
    if rb < ra:
        return b, a
    # same rank → alpha fallback: explicitly return two elements to satisfy Tuple[str, str]
    s = sorted([a, b])
    return s[0], s[1]

# ---------- Input parsing ----------
def parse_aspect_rows(rows: List[List[Any]]) -> List[AspectWindow]:
    """
    Expect each row like:
      [start_date, end_date, exact_date, ('Jup','Sxt','Moo'), angle_diff, angle_diff_360]
    If your header row is present, drop it before calling this.
    """
    out: List[AspectWindow] = []
    for r in rows:
        if len(r) < 4:
            continue
        start, end, exact, triple = r[0], r[1], r[2], r[3]
        if isinstance(triple, (list, tuple)) and len(triple) == 3:
            A, ASP, B = normalize_aspect_tuple((triple[0], triple[1], triple[2]))
            # align with KB canonical order
            A2, B2 = canonicalize_order(A, ASP, B)
            pair = (A2, ASP, B2)
            out.append(AspectWindow(start=str(start), end=str(end), exact=str(exact), pair=pair, raw={"row": r}))
    return out

# ---------- Lookup logic ----------
def resolve_card_id(pair: Tuple[str,str,str], by_triplet: Dict[Tuple[str,str,str],str]) -> Optional[str]:
    # direct match
    cid = by_triplet.get(pair)
    if cid:
        return cid
    # try reversed (if your KB accidentally stored a non-canonical order)
    rev = (pair[2], pair[1], pair[0])
    return by_triplet.get(rev)

# ---------- Phase helper ----------
def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def phase_for_today(start: str, exact: str, end: str, today: Optional[date] = None) -> str:
    """Classify which phase today is in. If today outside window, return 'out_of_window'."""
    t = today or date.today()
    ds, de, dx = _parse_date(start), _parse_date(end), _parse_date(exact)
    if ds <= t < dx:
        return "applying"
    elif t == dx:
        return "exact"
    elif dx < t <= de:
        return "separating"
    else:
        return "out_of_window"

# ---------- Report generation ----------
def render_item_md(card: Dict[str,Any], window: AspectWindow, theme: str = "career", lang: str = "en") -> str:
    loc = (card.get("locales") or {}).get(lang) or {}
    title = loc.get("title") or " · ".join(window.pair)
    core = (card.get("core_meaning") or "").strip()
    facets = card.get("facets") or {}
    facet_text = facets.get(theme) or ""
    risk = card.get("risk_notes") or []
    actions = (card.get("actionables") or {})
    ph = phase_for_today(window.start, window.exact, window.end)
    phase_actions = actions.get(ph, []) if ph in ("applying","exact","separating") else []
    # timing string
    timing = f"{window.start} → **{window.exact}** → {window.end}"
    # markdown
    md = []
    md.append(f"### {title}")
    md.append(f"*Pair:* **{window.pair[0]} {window.pair[1]} {window.pair[2]}**  \n*Window:* {timing}  \n*Phase now:* `{ph}`")
    if core:
        md.append(f"**Core meaning:** {core}")
    if facet_text:
        md.append(f"**{theme.capitalize()}:** {facet_text}")
    if risk:
        md.append("**Risks:** " + "; ".join(risk))
    if phase_actions:
        md.append(f"**Do now ({ph}):** " + " · ".join(phase_actions))
    else:
        # fallback: show all action buckets
        buckets = []
        for k in ("applying","exact","separating"):
            if actions.get(k):
                buckets.append(f"{k}: " + ", ".join(actions[k]))
        if buckets:
            md.append("**Actions:** " + " | ".join(buckets))
    return "\n\n".join(md)

def generate_report_from_rows(
    rows: List[List[Any]],
    kb_dir: str = KB_DIR,
    theme: str = "career",
    lang: str = "en",
    as_markdown: bool = True,
    today: Optional[date] = None
) -> str | List[Dict[str,Any]]:
    """
    rows: your computed windows (no header).
    theme: which facet to highlight (career, relationships, money, health_adj).
    lang: localization key to use from card.locales.
    Returns Markdown (default) or a list of dicts if as_markdown=False.
    """
    idx = load_index(os.path.join(kb_dir, "index.json"))
    by_triplet = idx["by_triplet"]
    id_to_path = idx["id_to_path"]

    windows = parse_aspect_rows(rows)

    md_blocks: List[str] = []
    out_struct: List[Dict[str,Any]] = []

    for w in windows:
        cid = resolve_card_id(w.pair, by_triplet)
        if not cid:
            # gracefully skip (or record a placeholder)
            missing = f"### {' · '.join(w.pair)}\n*Window:* {w.start} → **{w.exact}** → {w.end}\n> ⚠️ No Aspect Card found in KB for this pair."
            if as_markdown:
                md_blocks.append(missing)
            else:
                out_struct.append({
                    "pair": w.pair, "start": w.start, "exact": w.exact, "end": w.end,
                    "error": "card_not_found"
                })
            continue

        card = load_card(cid, id_to_path)
        if as_markdown:
            md_blocks.append(render_item_md(card, w, theme=theme, lang=lang))
        else:
            ph = phase_for_today(w.start, w.exact, w.end, today=today)
            out_struct.append({
                "pair": w.pair, "start": w.start, "exact": w.exact, "end": w.end,
                "card_id": cid,
                "title": ((card.get("locales") or {}).get(lang) or {}).get("title"),
                "core_meaning": card.get("core_meaning"),
                "facet": (card.get("facets") or {}).get(theme),
                "risks": card.get("risk_notes") or [],
                "phase": ph,
                "actions_now": (card.get("actionables") or {}).get(ph, [])
            })

    return "\n\n---\n\n".join(md_blocks) if as_markdown else out_struct

# ---------- Convenience: CLI-ish demo ----------
if __name__ == "__main__":
    # Demo input (paste your list without the header)
    sample = [
        ['2025-09-01','2025-09-07','2025-09-02',('Jup','Sxt','Moo'),0.1888,239.8111],
        ['2025-10-12','2025-12-12','2025-10-25',('Jup','Tri','Mar'),0.9788,119.0211],
        ['2025-11-05','2025-12-21','2025-11-28',('Sat','Tri','Mar'),0.9904,119.0095],
        ['2026-04-03','2026-04-18','2026-04-10',('Sat','Sxt','Ven'),0.8766,240.8766],
        ['2026-07-27','2026-08-04','2026-07-31',('Jup','Opp','Ven'),0.8237,0.8237],
        ['2026-08-21','2026-08-30','2026-08-25',('Jup','Con','Ura'),0.9548,359.0451],
    ]
    report_md = generate_report_from_rows(sample, theme="career", lang="en", as_markdown=True)
    print(report_md)
