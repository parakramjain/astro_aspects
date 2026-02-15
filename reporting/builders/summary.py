from __future__ import annotations

from datetime import datetime

import pytz
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..normalize import fmt_dt, get_lang_text, parse_iso_datetime, smart_no_orphan_last_word, to_local
from ..schema import ReportJson
from ..styles import PALETTE


def build_summary_story(data: ReportJson, config: ReportConfig, styles: Dict[str, any]) -> List:
    story: List = []

    lang = lang_for_text(config.language_mode)

    story.append(section_header(section_title("executive_summary", config), styles))
    story.append(Spacer(1, 6))

    ranked = _rank_timeline_items(data.timeline.items, config)
    opportunity = _first_with_nature(ranked, "positive")
    caution = _first_with_nature(ranked, "negative")
    action_item = opportunity or caution

    bullets: List[Tuple[str, str]] = []
    bullets.append((t("top_opportunity", lang), _headline_from_item(opportunity, config, lang)))
    bullets.append((t("top_caution", lang), _headline_from_item(caution, config, lang)))
    bullets.append((t("top_action", lang), _action_from_item(action_item, config, lang)))

    bullet_lines = []
    for label, text in bullets[: min(3, config.max_summary_bullets)]:
        line = smart_no_orphan_last_word(_truncate(text or "—", config.max_bullet_chars))
        bullet_lines.append(Paragraph(f"• {label}: {line}", styles["body"]))

    box = Table([[bullet_lines]], colWidths=[None])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE.summary_bg),
                ("LINEBEFORE", (0, 0), (0, -1), 3, PALETTE.accent),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(box)

    best_time = _best_time_from_items(ranked, config, lang)
    if best_time:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"{t('best_time', lang)}: {best_time}", styles["body_muted"]))

    return story


def _truncate(text: str, max_chars: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _nature_weight(nature: Optional[str]) -> int:
    if not nature:
        return 1
    s = str(nature).strip().lower()
    if s in {"positive", "negative", "challenging"}:
        return 2
    return 1


def _rank_timeline_items(items: Sequence[Any], config: ReportConfig) -> List[Any]:
    def _desc_present(it: Any) -> int:
        raw = getattr(it, "description", None)
        text = get_lang_text(raw, preferred="en", fallback="hi")
        text = text.strip()
        return 1 if text and text != "—" else 0

    def _exact_dt(it: Any) -> datetime:
        dt = parse_iso_datetime(getattr(it, "exactDate", None))
        return dt or datetime.max.replace(tzinfo=pytz.UTC)

    return sorted(
        items,
        key=lambda it: (
            -_desc_present(it),
            -_nature_weight(getattr(it, "aspectNature", None)),
            _exact_dt(it),
        ),
    )


def _first_with_nature(items: Sequence[Any], nature: str) -> Optional[Any]:
    for it in items:
        if str(getattr(it, "aspectNature", "")).strip().lower() == nature:
            return it
    return None


def _headline_from_item(item: Optional[Any], config: ReportConfig, lang: str) -> str:
    if not item:
        return ""
    raw = getattr(item, "description", None)
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    text = get_lang_text(raw, preferred=preferred, fallback=fallback)
    text = text.split(".")[0].strip() if text else ""
    return text.strip() or ""


def _action_from_item(item: Optional[Any], config: ReportConfig, lang: str) -> str:
    if not item:
        return ""
    key_points = getattr(item, "keyPoints", None)
    if not isinstance(key_points, dict):
        return ""
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    for phase in ("exact", "applying", "separating"):
        raw = key_points.get(phase)
        text = get_lang_text(raw, preferred=preferred, fallback=fallback)
        if text:
            first = text.split("\n")[0].strip()
            return _truncate(first, config.max_bullet_chars)
        if isinstance(raw, list) and raw:
            return _truncate(str(raw[0]).strip(), config.max_bullet_chars)
    return ""


def _best_time_from_items(items: Sequence[Any], config: ReportConfig, lang: str) -> str:
    if not items:
        return ""
    best_dt = None
    for it in items:
        dt = parse_iso_datetime(getattr(it, "exactDate", None))
        if dt and (best_dt is None or dt < best_dt):
            best_dt = dt
    if not best_dt:
        return ""
    return fmt_dt(to_local(best_dt, config.locale_timezone), lang)
