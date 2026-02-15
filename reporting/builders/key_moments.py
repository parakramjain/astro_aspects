from __future__ import annotations

from typing import Any, Dict, List

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..normalize import (
    aspect_is_challenging,
    aspect_is_positive,
    fmt_dt,
    get_lang_text,
    parse_iso_date,
    parse_iso_datetime,
    smart_no_orphan_last_word,
    to_local,
)
from ..schema import ReportJson
from ..styles import PALETTE


def _advice_from_keypoints(key_points: Any, config: ReportConfig) -> str:
    if not isinstance(key_points, dict):
        return ""
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"

    for phase in ("exact", "applying"):
        raw = key_points.get(phase)
        if isinstance(raw, dict):
            txt = get_lang_text(raw, preferred=preferred, fallback=fallback)
            first = txt.split("\n")[0].strip() if txt else ""
            if first:
                return first
        if isinstance(raw, list) and raw:
            return str(raw[0]).strip()
    return ""


def build_key_moments_story(data: ReportJson, config: ReportConfig, styles: Dict[str, any]) -> List:
    story: List = []
    lang = lang_for_text(config.language_mode)
    story.append(section_header(section_title("key_moments", config), styles))
    story.append(Spacer(1, 6))

    items = list(data.timeline.items or [])
    items = [it for it in items if getattr(it, "exactDate", None)]
    items.sort(key=lambda it: (parse_iso_date(getattr(it, "exactDate", None)) or parse_iso_date("9999-12-31"), getattr(it, "aspect", "")))

    positives = [it for it in items if aspect_is_positive(getattr(it, "aspectNature", None))][:3]
    negatives = [it for it in items if aspect_is_challenging(getattr(it, "aspectNature", None))][:2]
    chosen = (positives + negatives)[: config.max_key_moments]

    if not chosen:
        story.append(Paragraph(t("no_major_signals", lang), styles["body"]))
        return story

    rows = [[Paragraph(t("date", lang), styles["table_header"]), Paragraph(t("aspect", lang), styles["table_header"]), Paragraph(t("action", lang), styles["table_header"])]]

    for it in chosen:
        advice = _advice_from_keypoints(it.keyPoints, config) or "—"
        dt = parse_iso_datetime(getattr(it, "exactDate", None))
        date_label = fmt_dt(to_local(dt, config.locale_timezone), lang) if dt else str(getattr(it, "exactDate", ""))[:16]
        rows.append(
            [
                Paragraph(date_label, styles["body"]),
                Paragraph(smart_no_orphan_last_word(str(getattr(it, "aspect", ""))), styles["body"]),
                Paragraph(smart_no_orphan_last_word(advice), styles["body"]),
            ]
        )

    tbl = Table(rows, colWidths=[80, 170, None])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE.accent),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(tbl)
    return story
