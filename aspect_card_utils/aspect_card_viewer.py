"""Aspect Card Viewer Components

HTML rendering helpers to present aspect card data in a structured, readable format
instead of a raw JSON textarea. Uses Tailwind classes (already loaded by parent page).

Design goals:
- Bilingual aware: gracefully render legacy (string/list) or new bilingual dict structures.
- Compact but scannable: group semantic sections; collapsible for large blocks.
- Pure functions returning HTML strings; no FastAPI dependency here.

Public entrypoints:
- render_card_readonly(card: AspectCardModel) -> str
- render_section_grid(title: str, sections: list[tuple[str,str]]) -> str

Note: AspectCardModel is imported from aspect_card_mgmt to avoid duplication.
"""
from __future__ import annotations
from typing import Any, Dict, List, Union
from html import escape

try:
    # Import the Pydantic model from management module
    from .aspect_card_mgmt import AspectCardModel  # type: ignore
except Exception:  # pragma: no cover
    AspectCardModel = Any  # type: ignore

# ------------- Utility Normalizers -------------

def _norm_bilingual(val: Any) -> Dict[str, Any]:
    """Return a dict with 'en' and 'hi' keys for bilingual display.
    Accepts legacy variants (str, list) and bilingual dicts.
    """
    if isinstance(val, dict) and ("en" in val or "hi" in val):
        en = val.get("en")
        hi = val.get("hi")
        return {
            "en": en if en is not None else "",
            "hi": hi if hi is not None else "",
        }
    # legacy string/list
    if isinstance(val, list):
        text = ", ".join([str(v) for v in val])
    else:
        text = str(val)
    return {"en": text, "hi": ""}


def _norm_facet_block(facets: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for key, raw in facets.items():
        norm = _norm_bilingual(raw)
        out[key] = {"en": str(norm.get("en", "")), "hi": str(norm.get("hi", ""))}
    return out


def _norm_actionables(actionables: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    out: Dict[str, Dict[str, List[str]]] = {}
    for phase, payload in actionables.items():
        if isinstance(payload, dict) and ("en" in payload or "hi" in payload):
            en_list = payload.get("en") or []
            hi_list = payload.get("hi") or []
            if not isinstance(en_list, list):
                en_list = [str(en_list)]
            if not isinstance(hi_list, list):
                hi_list = [str(hi_list)]
            out[phase] = {"en": en_list, "hi": hi_list}
        else:
            # legacy list
            items = payload if isinstance(payload, list) else [str(payload)]
            out[phase] = {"en": [str(i) for i in items], "hi": []}
    return out


def _norm_embedding_sections(retrieval: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    emb = retrieval.get("embedding_sections", {})
    out: Dict[str, Dict[str, str]] = {}
    for sec, raw in emb.items():
        out[sec] = _norm_bilingual(raw)
    return out

# ------------- HTML Builders -------------

def _badge(text: str, color: str = "indigo") -> str:
    if not text:
        return ""
    return f"<span class='inline-block px-2 py-0.5 text-xs rounded bg-{color}-100 text-{color}-700 mr-1 mb-1'>{escape(text)}</span>"


def _collapsible(summary: str, inner_html: str, open: bool=False) -> str:
    return (
        f"<details class='group border rounded-lg bg-white shadow-sm p-3 mb-3' {'open' if open else ''}>"
        f"<summary class='cursor-pointer font-semibold text-sm text-gray-800 flex items-center justify-between'>"
        f"{escape(summary)}"
        f"<span class='text-xs text-gray-500 group-open:hidden'>show</span>"
        f"<span class='text-xs text-gray-500 hidden group-open:inline'>hide</span>"
        f"</summary>"
        f"<div class='pt-2 text-sm leading-relaxed'>{inner_html}</div>"
        f"</details>"
    )


def _render_list(items: List[str]) -> str:
    if not items:
        return "<em class='text-gray-400'>none</em>"
    return "<ul class='list-disc ml-5 space-y-1'>" + "".join([f"<li>{escape(i)}</li>" for i in items]) + "</ul>"


def render_section_grid(title: str, sections: List[tuple[str, str]]) -> str:
    cards = []
    for name, content in sections:
        cards.append(
            f"<div class='border rounded-lg p-3 bg-gray-50'>"
            f"<h4 class='font-medium text-sm mb-1'>{escape(name)}</h4>"
            f"<div class='text-sm whitespace-pre-line'>{escape(content)}</div>"
            f"</div>"
        )
    grid = "<div class='grid grid-cols-1 md:grid-cols-2 gap-3'>" + "".join(cards) + "</div>"
    return f"<section class='mb-4'><h3 class='text-base font-semibold mb-2'>{escape(title)}</h3>{grid}</section>"

# ------------- Main Renderer -------------

def render_card_readonly(card: Any) -> str:
    # Header metadata
    pair_str = f"{card.pair[0]} • {card.pair[1]} • {card.pair[2]}"
    provenance = card.provenance or {}
    reviewed_at = provenance.get("reviewed_at", "—")
    author = provenance.get("author", "—")

    # core meaning
    cm = _norm_bilingual(card.core_meaning)

    # facets
    facets = _norm_facet_block(card.facets)

    # life events
    life_events = _norm_bilingual(card.life_event_type)

    # risk notes
    risks = _norm_bilingual(card.risk_notes)

    # actionables
    actionables = _norm_actionables(card.actionables)

    # keywords/qualities/themes
    keywords = _norm_bilingual(card.keywords)
    quality_tags = _norm_bilingual(card.quality_tags)
    themes = _norm_bilingual(card.theme_overlays)

    # retrieval excerpts
    embeddings = _norm_embedding_sections(card.retrieval)

    # weights quick view (legacy structure retained)
    weights_hint = card.weights_hint
    modifiers = card.modifiers

    # locales
    locales = card.locales
    en_title = getattr(locales.get('en'), 'title', None) if locales.get('en') else None
    if isinstance(locales.get('en'), dict):
        en_title = locales['en'].get('title')
    hi_title = getattr(locales.get('hi'), 'title', None) if locales.get('hi') else None
    if isinstance(locales.get('hi'), dict):
        hi_title = locales['hi'].get('title')

    parts: List[str] = []
    parts.append(
        f"<div class='mb-4'><div class='flex items-start justify-between flex-wrap gap-2'>"
        f"<div><h2 class='text-xl font-semibold text-gray-800'>{escape(card.id)}</h2>"
        f"<p class='text-sm text-gray-600'>{escape(pair_str)}</p></div>"
        f"<div class='text-xs text-gray-500'>Reviewed: {escape(reviewed_at)}<br/>Author: {escape(author)}</div>"
        f"</div>"
        f"<div class='mt-2 text-sm'><strong class='font-medium'>English Title:</strong> {escape(en_title or '')} &nbsp; <strong class='font-medium'>Hindi Title:</strong> {escape(hi_title or '')}</div>"
        f"</div>"
    )

    core_hi_html = escape(cm['hi']) if cm['hi'] else "<em class='text-gray-400'>—</em>"
    parts.append(_collapsible(
        "Core Meaning",
        (
            "<div class='grid grid-cols-1 md:grid-cols-2 gap-4'>"
            "<div><h4 class='font-medium mb-1'>English</h4><p class='text-sm whitespace-pre-line'>" + escape(cm['en']) + "</p></div>"
            "<div><h4 class='font-medium mb-1'>Hindi</h4><p class='text-sm whitespace-pre-line'>" + core_hi_html + "</p></div>"
            "</div>"
        ),
        open=True
    ))

    # Facets section
    facet_cards = []
    for facet_name, payload in facets.items():
        facet_hi_html = escape(payload['hi']) if payload['hi'] else "<em class='text-gray-400'>—</em>"
        facet_cards.append(
            "<div class='border rounded-lg p-3 bg-white shadow-sm'><h4 class='font-medium text-sm mb-1'>" + escape(facet_name) + "</h4>"
            + "<div class='text-xs text-gray-500 mb-1'>English</div><div class='text-sm mb-2 whitespace-pre-line'>" + escape(payload['en']) + "</div>"
            + "<div class='text-xs text-gray-500 mb-1'>Hindi</div><div class='text-sm whitespace-pre-line'>" + facet_hi_html + "</div></div>"
        )
    parts.append(_collapsible("Facets", "<div class='grid grid-cols-1 md:grid-cols-2 gap-3'>" + "".join(facet_cards) + "</div>") )

    # Life events / Risks
    parts.append(_collapsible("Life Event Types", _render_list(life_events['en']) + ("<hr class='my-3'/>" + _render_list(life_events['hi'])) if life_events['hi'] else ""))
    parts.append(_collapsible("Risk Notes", _render_list(risks['en']) + ("<hr class='my-3'/>" + _render_list(risks['hi'])) if risks['hi'] else ""))

    # Actionables
    action_html_blocks = []
    for phase in ["applying","exact","separating"]:
        if phase in actionables:
            data = actionables[phase]
            action_html_blocks.append(
                f"<div class='border rounded-lg p-3 bg-gray-50'><h4 class='font-semibold text-xs mb-2 uppercase tracking-wide'>{phase}</h4>"
                f"<div class='mb-2'><h5 class='text-xs font-medium text-gray-600'>English</h5>{_render_list(data['en'])}</div>"
                f"<div><h5 class='text-xs font-medium text-gray-600'>Hindi</h5>{_render_list(data['hi'])}</div></div>"
            )
    parts.append(_collapsible("Actionables", "<div class='grid grid-cols-1 md:grid-cols-3 gap-3'>" + "".join(action_html_blocks) + "</div>") )

    # Keywords / Tags / Themes
    kw_html = "<div><h4 class='font-medium text-sm mb-1'>Keywords (EN)</h4>" + "".join([_badge(k) for k in keywords['en']]) + "</div>"
    if keywords['hi']:
        kw_html += "<div class='mt-2'><h4 class='font-medium text-sm mb-1'>Keywords (HI)</h4>" + "".join([_badge(k, 'green') for k in keywords['hi']]) + "</div>"
    qt_html = "<div class='mt-3'><h4 class='font-medium text-sm mb-1'>Quality Tags</h4>" + "".join([_badge(k, 'purple') for k in quality_tags['en']]) + "</div>"
    theme_html = "<div class='mt-3'><h4 class='font-medium text-sm mb-1'>Theme Overlays</h4>" + "".join([_badge(k, 'yellow') for k in themes['en']]) + "</div>"
    parts.append(_collapsible("Keywords & Tags", kw_html + qt_html + theme_html))

    # Retrieval Embeddings
    emb_blocks = []
    for sec, payload in embeddings.items():
        hi_emb_html = escape(payload.get('hi','')) if payload.get('hi','') else "<em class='text-gray-400'>—</em>"
        emb_blocks.append(
            "<div class='border rounded-lg p-3 bg-white shadow-sm'><h4 class='font-medium text-xs mb-1 uppercase tracking-wide'>" + escape(sec) + "</h4>"
            + "<div class='text-xs text-gray-500 mb-1'>English</div><div class='text-sm whitespace-pre-line mb-2'>" + escape(payload.get('en','')) + "</div>"
            + "<div class='text-xs text-gray-500 mb-1'>Hindi</div><div class='text-sm whitespace-pre-line'>" + hi_emb_html + "</div></div>"
        )
    parts.append(_collapsible("Retrieval Embedding Sections", "<div class='grid grid-cols-1 md:grid-cols-2 gap-3'>" + "".join(emb_blocks) + "</div>") )

    # Weights / Modifiers
    weights_html = escape(str(weights_hint)) if weights_hint else "<em class='text-gray-400'>none</em>"
    modifiers_html = escape(str(modifiers)) if modifiers else "<em class='text-gray-400'>none</em>"
    parts.append(_collapsible("Weights & Modifiers", f"<div class='text-xs'><strong>weights_hint:</strong><pre class='whitespace-pre-wrap mt-1'>{weights_html}</pre><strong class='block mt-2'>modifiers:</strong><pre class='whitespace-pre-wrap mt-1'>{modifiers_html}</pre></div>") )

    return "".join(parts)

__all__ = ["render_card_readonly", "render_section_grid"]
