from __future__ import annotations

from typing import Dict, List

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..i18n import lang_for_text, section_title, t
from ..layout import report_title_key
from ..normalize import fmt_date, parse_iso_datetime, to_local
from ..schema import ReportJson
from ..styles import PALETTE


def build_cover_story(data: ReportJson, config: ReportConfig, styles: Dict[str, any]) -> List:
    story: List = []

    lang = lang_for_text(config.language_mode)
    dob_dt = parse_iso_datetime(data.input.dateOfBirth)
    start_dt = parse_iso_datetime(data.input.reportStartDate)
    dob_text = fmt_date(to_local(dob_dt, config.locale_timezone), lang) if dob_dt else data.input.dateOfBirth
    start_text = fmt_date(to_local(start_dt, config.locale_timezone), lang) if start_dt else data.input.reportStartDate

    story.append(Spacer(1, 24 * mm))
    story.append(Paragraph(section_title(report_title_key(config.report_type), config), styles["cover_title"]))
    story.append(
        Paragraph(
            f"{config.report_type} • {data.input.timePeriod} • {start_text}",
            styles["cover_subtitle"],
        )
    )
    story.append(Spacer(1, 10 * mm))

    details = [
        [Paragraph(t("name", lang), styles["label"]), Paragraph(data.input.name, styles["value"])],
        [Paragraph(t("dob", lang), styles["label"]), Paragraph(dob_text, styles["value"])],
        [Paragraph(t("pob", lang), styles["label"]), Paragraph(data.input.placeOfBirth, styles["value"])],
        [
            Paragraph(t("report_period", lang), styles["label"]),
            Paragraph(f"{data.input.timePeriod} (start: {start_text})", styles["value"]),
        ],
        [Paragraph(t("language", lang), styles["label"]), Paragraph(config.language_mode, styles["value"])],
    ]

    tbl = Table(details, colWidths=[42 * mm, None])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE.cover_card_bg),
                ("LINEBEFORE", (0, 0), (0, -1), 3, PALETTE.accent),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PALETTE.divider),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(tbl)
    story.append(Spacer(1, 18 * mm))

    if lang == "EN":
        story.append(Paragraph("• This report is for personal guidance only.", styles["small"]))
        story.append(Paragraph("• Use your judgment before making decisions.", styles["small"]))
        story.append(Paragraph("• It indicates possibilities, not certainties.", styles["small"]))
    else:
        story.append(Paragraph("• यह रिपोर्ट केवल व्यक्तिगत मार्गदर्शन हेतु है।", styles["small"]))
        story.append(Paragraph("• कोई भी निर्णय लेने से पहले अपने विवेक का उपयोग करें।", styles["small"]))
        story.append(Paragraph("• यह भविष्यवाणी नहीं, संभावनाओं का संकेत है।", styles["small"]))

    return story
