from __future__ import annotations

import logging
from datetime import datetime

import pytz
from typing import Any, Dict, List, Tuple

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..normalize import (
    fmt_dt,
    get_lang_text,
    parse_iso_datetime,
    pick_keywords,
    smart_no_orphan_last_word,
    to_local,
)
from ..schema import ReportJson, TimelineItem
from ..styles import PALETTE

logger = logging.getLogger(__name__)


def _badge_for_nature(nature: str | None) -> Tuple[Any, Any, str]:
    if not nature:
        return (PALETTE.badge_neutral_bg, PALETTE.muted, "Neutral")
    s = str(nature).strip().lower()
    if s == "positive":
        return (PALETTE.badge_positive_bg, PALETTE.success, "Positive")
    if s in {"negative", "challenging"}:
        return (PALETTE.badge_challenging_bg, PALETTE.warning, "Challenging")
    return (PALETTE.badge_neutral_bg, PALETTE.muted, "Mixed")


def _truncate(text: str, max_chars: int = 420) -> str:
    """Deterministic truncation; approximates 4-line constraint."""
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _truncate_short(text: str, max_chars: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _action_bullets(key_points: Any, config: ReportConfig) -> List[str]:
    if not isinstance(key_points, dict):
        return []

    # prefer exact, else applying, else separating
    for phase in ("exact", "applying", "separating"):
        raw = key_points.get(phase)
        if isinstance(raw, dict):
            preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
            fallback = "en" if preferred == "hi" else "hi"
            text = get_lang_text(raw, preferred=preferred, fallback=fallback)
            items = [x.strip() for x in text.split("\n") if x.strip()]
            if items:
                return items[:3]
        if isinstance(raw, list):
            items = [str(x).strip() for x in raw if str(x).strip()]
            if items:
                return items[:3]

    return []


def _action_first(key_points: Any, config: ReportConfig) -> str:
    items = _action_bullets(key_points, config)
    return items[0] if items else ""


def _facet_bullets(facets: Any, config: ReportConfig) -> List[str]:
    if not isinstance(facets, dict):
        return []

    lang = lang_for_text(config.language_mode)
    keys = [
        ("career", "करियर", "Career"),
        ("relationships", "रिश्ते", "Relationships"),
        ("money", "धन", "Money"),
        ("health_adj", "स्वास्थ्य", "Health"),
    ]
    out: List[str] = []

    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"

    for k, label_hi, label_en in keys:
        raw = facets.get(k)
        txt = get_lang_text(raw, preferred=preferred, fallback=fallback)
        if txt:
            label = label_hi if lang == "HI" else label_en
            out.append(f"{label}: {txt}")
        if len(out) >= 4:
            break
    return out


def _facet_tags(facets: Any, config: ReportConfig) -> List[str]:
    if not isinstance(facets, dict):
        return []

    lang = lang_for_text(config.language_mode)
    keys = [
        ("career", "करियर", "Career"),
        ("relationships", "रिश्ते", "Relationships"),
        ("money", "धन", "Money"),
        ("health_adj", "स्वास्थ्य", "Health"),
    ]
    out: List[str] = []
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    for k, hi_label, en_label in keys:
        txt = get_lang_text(facets.get(k), preferred=preferred, fallback=fallback)
        if txt and txt.strip() and txt.strip() != "—":
            out.append(hi_label if lang == "HI" else en_label)
        if len(out) >= 4:
            break
    return out


def _is_empty_item(item: TimelineItem, config: ReportConfig) -> bool:
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"

    desc = get_lang_text(item.description, preferred=preferred, fallback=fallback).strip()
    actions = _action_bullets(item.keyPoints, config)
    keywords = pick_keywords(item, config)

    desc_ok = bool(desc and desc != "—")
    action_ok = bool(actions)
    kw_ok = bool([k for k in keywords if k and k != "—"])
    return not (desc_ok or action_ok or kw_ok)


def _timeline_card(item: TimelineItem, config: ReportConfig, styles: Dict[str, Any]) -> KeepTogether:
    bg, fg, _ = _badge_for_nature(item.aspectNature)

    title = Paragraph(smart_no_orphan_last_word(item.aspect), styles["subheader"])

    nature = str(item.aspectNature or "").strip().lower()
    bg_override = PALETTE.badge_challenging_bg if nature == "negative" else PALETTE.badge_positive_bg

    badge = Table(
        [[Paragraph(smart_no_orphan_last_word(str(item.aspectNature or "Mixed")), styles["badge"])]],
        colWidths=[58],
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_override),
                ("TEXTCOLOR", (0, 0), (-1, -1), fg),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    header_row = Table([[title, badge]], colWidths=[None, 60])
    header_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    lang = lang_for_text(config.language_mode)
    def _fmt_dt(value: Any) -> str:
        dt = parse_iso_datetime(value)
        if not dt:
            return str(value)
        return fmt_dt(to_local(dt, config.locale_timezone), lang)

    date_line = Paragraph(
        f"{t('start', lang)}: {_fmt_dt(item.startDate)}  |  {t('peak', lang)}: {_fmt_dt(item.exactDate)}  |  {t('end', lang)}: {_fmt_dt(item.endDate)}",
        styles["body_muted"],
    )

    desc_raw = item.description
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    desc = get_lang_text(desc_raw, preferred=preferred, fallback=fallback)
    desc = _truncate(desc)
    desc = smart_no_orphan_last_word(desc)

    desc_para = Paragraph(desc or "—", styles["body"])

    left_bullets = _action_bullets(item.keyPoints, config)
    right_bullets = _facet_bullets(item.facetsPoints, config)

    left_lines = [Paragraph(t("action", lang), styles["subheader"])]+[Paragraph(f"• {smart_no_orphan_last_word(x)}", styles["body"]) for x in (left_bullets or ["—"]) ]
    right_lines = [Paragraph(t("main_areas", lang), styles["subheader"])]+[Paragraph(f"• {smart_no_orphan_last_word(x)}", styles["body"]) for x in (right_bullets or ["—"]) ]

    two_col = Table([[left_lines, right_lines]], colWidths=[None, None])
    two_col.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    keywords = pick_keywords(item, config)
    kw_line = Paragraph(
        f"{t('keywords', lang)}: {'  • '.join(keywords) if keywords else '—'}",
        styles["small"],
    )

    card = Table(
        [[header_row], [date_line], [desc_para], [two_col], [kw_line]],
        colWidths=[None],
    )
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE.card_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return KeepTogether([card, Spacer(1, 6 * mm)])


def _timeline_card_compact(item: TimelineItem, config: ReportConfig, styles: Dict[str, Any]) -> KeepTogether:
    lang = lang_for_text(config.language_mode)
    bg, fg, _ = _badge_for_nature(item.aspectNature)

    title = Paragraph(smart_no_orphan_last_word(item.aspect), styles["subheader"])
    badge = Table([[Paragraph(smart_no_orphan_last_word(str(item.aspectNature or "Mixed")), styles["badge"]) ]], colWidths=[58])
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TEXTCOLOR", (0, 0), (-1, -1), fg),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    header_row = Table([[title, badge]], colWidths=[None, 62])
    header_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    def _fmt_dt(value: Any) -> str:
        dt = parse_iso_datetime(value)
        if not dt:
            return str(value)
        return fmt_dt(to_local(dt, config.locale_timezone), lang)

    date_line = Paragraph(
        f"{t('start', lang)}: {_fmt_dt(item.startDate)}  |  {t('peak', lang)}: {_fmt_dt(item.exactDate)}  |  {t('end', lang)}: {_fmt_dt(item.endDate)}",
        styles["body_muted"],
    )

    desc_raw = item.description
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    desc = get_lang_text(desc_raw, preferred=preferred, fallback=fallback)
    desc = desc.split(".")[0].strip() if desc else ""
    desc = _truncate_short(desc, 140)
    desc_para = Paragraph(desc or "—", styles["body"])

    action_text = _action_first(item.keyPoints, config)
    action_line = Paragraph(
        f"{t('action_today', lang)}: {_truncate_short(action_text or '—', config.max_bullet_chars)}",
        styles["body"],
    )

    tags = _facet_tags(item.facetsPoints, config)
    tags_line = None
    if tags:
        tags_line = Paragraph(f"{t('areas_impacted', lang)}: {' • '.join(tags)}", styles["small"])

    rows = [header_row, date_line, desc_para, action_line]
    if tags_line is not None:
        rows.append(tags_line)

    card = Table([[r] for r in rows], colWidths=[None])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE.card_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return KeepTogether([card, Spacer(1, 6 * mm)])


def build_timeline_story(data: ReportJson, config: ReportConfig, styles: Dict[str, Any], report_id: str | None = None) -> List:
    story: List = []
    story.append(section_header(section_title("timeline", config), styles))
    story.append(Spacer(1, 6))

    items = data.timeline.items or []
    if not items:
        lang = lang_for_text(config.language_mode)
        story.append(Paragraph(t("no_major_signals", lang), styles["body"]))
        return story

    skipped_empty = 0
    if config.hide_empty_items:
        filtered = []
        for it in items:
            if _is_empty_item(it, config):
                skipped_empty += 1
                continue
            filtered.append(it)
        items = filtered

    if not items:
        lang = lang_for_text(config.language_mode)
        story.append(Paragraph(t("no_major_signals", lang), styles["body"]))
        if report_id:
            logger.info(
                "timeline_counts",
                extra={
                    "report_id": report_id,
                    "timeline_total": len(data.timeline.items or []),
                    "timeline_rendered": 0,
                    "skipped_empty": skipped_empty,
                },
            )
        return story

    items.sort(
        key=lambda it: (
            parse_iso_datetime(getattr(it, "exactDate", None)) or datetime.max.replace(tzinfo=pytz.UTC),
            getattr(it, "aspect", ""),
        )
    )

    if config.density == "COMPACT":
        items = items[: config.max_timeline_cards]
    elif config.density == "STANDARD":
        items = items[: config.max_timeline_cards_standard]

    rendered = 0
    print("in timeline.py, items count:", len(items))
    for it in items:
        try:
            if config.density == "COMPACT":
                story.append(_timeline_card_compact(it, config, styles))
            else:
                story.append(_timeline_card(it, config, styles))
            rendered += 1
        except Exception as exc:
            logger.exception("timeline_item_skipped", extra={"error": str(exc)})
            continue

    if report_id:
        logger.info(
            "timeline_counts",
            extra={
                "report_id": report_id,
                "timeline_total": len(data.timeline.items or []),
                "timeline_rendered": rendered,
                "skipped_empty": skipped_empty,
            },
        )

    return story
