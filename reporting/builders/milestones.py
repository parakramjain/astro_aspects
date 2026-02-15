from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List

from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..normalize import fmt_date, get_lang_text, normalize_life_event_description, parse_iso_date, parse_iso_datetime, smart_no_orphan_last_word, to_local
from ..schema import ReportJson
from ..styles import PALETTE

logger = logging.getLogger(__name__)


PLANET_MAP = {
    "SUN": "Sun",
    "MOO": "Moon",
    "MER": "Mercury",
    "VEN": "Venus",
    "MAR": "Mars",
    "JUP": "Jupiter",
    "SAT": "Saturn",
    "URA": "Uranus",
    "NEP": "Neptune",
    "PLU": "Pluto",
}

ASPECT_MAP = {
    "CON": "conjunct",
    "OPP": "opposition",
    "SXT": "sextile",
    "SQR": "square",
    "TRI": "trine",
}


def _humanize_transit_window(text: str) -> str:
    s = text.strip()
    if not s.endswith("transit window"):
        return ""
    core = s.replace("transit window", "").strip()
    parts = core.split()
    if len(parts) != 3:
        return ""
    p1, asp, p2 = parts
    p1 = PLANET_MAP.get(p1.upper(), p1)
    p2 = PLANET_MAP.get(p2.upper(), p2)
    asp = ASPECT_MAP.get(asp.upper(), asp.lower())
    return f"Transit window: {p1} {asp} {p2}"


def build_milestones_story(data: ReportJson, config: ReportConfig, styles: Dict[str, Any], report_id: str | None = None) -> List:
    story: List = []
    story.append(section_header(section_title("milestones", config), styles))
    story.append(Spacer(1, 6))

    events = data.lifeEvents or []
    if not events:
        lang = lang_for_text(config.language_mode)
        story.append(Paragraph(t("no_major_signals", lang), styles["body"]))
        return story

    lang = lang_for_text(config.language_mode)
    report_start = parse_iso_datetime(data.input.reportStartDate)
    filtered: List[Any] = []

    if config.report_type == "DAILY" and config.density != "DETAILED" and report_start:
        cutoff = report_start + timedelta(days=config.milestone_window_days)
        for ev in events:
            sd = parse_iso_datetime(ev.startDate) or parse_iso_datetime(ev.exactDate) or parse_iso_datetime(ev.endDate)
            if sd and sd <= cutoff:
                filtered.append(ev)
        events = filtered

    if config.density == "COMPACT":
        events = events[: config.max_milestones]

    buckets: Dict[str, List[Any]] = defaultdict(list)
    for ev in events:
        d = parse_iso_date(ev.exactDate) or parse_iso_date(ev.startDate) or parse_iso_date(ev.endDate)
        year = str(d.year) if d else t("other", lang)
        buckets[year].append(ev)

    years_sorted = sorted(buckets.keys())
    show_year_headers = len(years_sorted) > 1

    rendered = 0
    for year in years_sorted:
        if show_year_headers:
            year_chip = Table([[Paragraph(str(year), styles["subheader"]) ]], colWidths=[None])
            year_chip.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALETTE.accent_light),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(year_chip)
        for ev in buckets[year]:
            try:
                desc_val = normalize_life_event_description(ev.description)
                preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
                fallback = "en" if preferred == "hi" else "hi"

                desc_text = get_lang_text(desc_val, preferred=preferred, fallback=fallback)
                desc_lines = [x.strip() for x in desc_text.split("\n") if x.strip()]

                transit_line = ""
                if desc_text and "transit window" in desc_text.lower():
                    transit_line = _humanize_transit_window(desc_text)

                if transit_line and len(desc_lines) == 1 and desc_lines[0].strip() == desc_text.strip():
                    desc_lines = [transit_line]

                if config.density == "COMPACT" and transit_line and desc_lines == [transit_line]:
                    continue

                header = f"{ev.eventType or ''} | {ev.aspectNature or ''}"
                exact_dt = parse_iso_datetime(ev.exactDate) if ev.exactDate else None
                exact_label = fmt_date(to_local(exact_dt, config.locale_timezone), lang) if exact_dt else (ev.exactDate or "—")
                meta = f"{ev.timePeriod or ''}  ({t('peak', lang)}: {exact_label})"

                lines: List = [
                    Paragraph(smart_no_orphan_last_word(header.strip() or ev.aspect), styles["subheader"]),
                    Paragraph(smart_no_orphan_last_word(meta.strip()), styles["small"]),
                ]
                if desc_lines:
                    for dl in desc_lines[:6]:
                        lines.append(Paragraph(f"• {smart_no_orphan_last_word(dl)}", styles["body"]))
                else:
                    if config.density != "COMPACT":
                        lines.append(Paragraph("• —", styles["body"]))
                    else:
                        continue

                card = Table([[lines]], colWidths=[None])
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

                story.append(KeepTogether([card, Spacer(1, 8)]))
                rendered += 1
            except Exception as exc:
                logger.exception("milestone_skipped", extra={"error": str(exc)})
                continue

    if report_id:
        logger.info(
            "milestones_counts",
            extra={
                "report_id": report_id,
                "milestones_rendered": rendered,
            },
        )

    return story
