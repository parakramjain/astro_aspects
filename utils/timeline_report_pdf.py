from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from schemas import TimelineRequest


def _resolve_output_path(output_path: Optional[str], payload: TimelineRequest) -> str:
    if output_path:
        return output_path
    safe_name = "_".join(str(payload.name).split()) if payload.name else "timeline"
    filename = f"{safe_name}__{payload.reportStartDate}__timeline.pdf"
    base_dir = Path(__file__).resolve().parents[1]
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / filename)


def _resolve_plot_image(timeline_plot: Any) -> Optional[str]:
    if timeline_plot is None:
        return None
    if isinstance(timeline_plot, (str, os.PathLike)):
        path = str(timeline_plot)
        if os.path.isfile(path):
            return path
        return None
    if hasattr(timeline_plot, "savefig"):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        timeline_plot.savefig(tmp.name, dpi=300, bbox_inches="tight")
        return tmp.name
    return None


def _get_devanagari_font_name() -> str:
    base_dir = Path(__file__).resolve().parents[1]
    font_dir = base_dir / "reporting" / "fonts"
    regular = font_dir / "NotoSansDevanagari-Regular.ttf"
    bold = font_dir / "NotoSansDevanagari-Bold.ttf"

    if regular.is_file():
        try:
            registered = set(pdfmetrics.getRegisteredFontNames())
            if "NotoSansDevanagari" not in registered:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(regular)))
            if bold.is_file() and "NotoSansDevanagari-Bold" not in registered:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(bold)))
                pdfmetrics.registerFontFamily(
                    "NotoSansDevanagari",
                    normal="NotoSansDevanagari",
                    bold="NotoSansDevanagari-Bold",
                )
            return "NotoSansDevanagari"
        except Exception:
            return "Helvetica"
    return "Helvetica"


def _get_cinzel_font_name() -> str:
    base_dir = Path(__file__).resolve().parents[1]
    font_path = base_dir / "reporting" / "fonts" / "Cinzel-VariableFont_wght.ttf"
    if font_path.is_file():
        try:
            registered = set(pdfmetrics.getRegisteredFontNames())
            if "Cinzel" not in registered:
                pdfmetrics.registerFont(TTFont("Cinzel", str(font_path)))
            return "Cinzel"
        except Exception:
            return "Helvetica"
    return "Helvetica"


def _format_ai_summary(ai_summary: str, font_name: str) -> list[Any]:
    if not ai_summary:
        return []
    try:
        summary_data = json.loads(ai_summary)
    except Exception:
        return []

    chunks = summary_data.get("chunks")
    if not isinstance(chunks, list):
        return []

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "AiSummaryHeader",
        parent=styles["Heading2"],
        fontName=font_name,
        alignment=TA_CENTER,
    )
    body_style = ParagraphStyle(
        "AiSummaryBody",
        parent=styles["BodyText"],
        fontName=font_name,
        alignment=TA_JUSTIFY,
    )

    flowables: list[Any] = [Paragraph("Summary Report and Advice", header_style), Spacer(1, 12)]

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        start_date = escape(str(chunk.get("startDate", "")))
        end_date = escape(str(chunk.get("endDate", "")))
        summary_text = escape(str(chunk.get("summary", "")))
        highlights = chunk.get("highlights", {}) if isinstance(chunk.get("highlights"), dict) else {}
        focus = escape(str(highlights.get("focus", "")))
        supportive = escape(str(highlights.get("supportiveActions", "")))
        cautions = escape(str(highlights.get("cautions", "")))

        parts = [
            f"<b>Starting {start_date} till {end_date}</b>",
            f"-----"*27,
            summary_text,
            f" ",
            f"<b>Focus:</b> {focus}",
            f"<b>Supportive Actions:</b> {supportive}",
            f"<b>Cautions:</b> {cautions}",
        ]
        block = "<br/>".join([p for p in parts if p and p != "<b> to </b>"])
        flowables.append(KeepTogether([Paragraph(block, body_style), Spacer(1, 10)]))

    return flowables

def create_timeline_pdf_report(
    payload: TimelineRequest,
    timeline_plot: Any,
    timeline_description: str,
    ai_summary: Optional[str] = None,
    output_path: Optional[str] = None,
    lang_code: str = "en"
) -> str:
    """Create a PDF report for timeline plot and description.

    timeline_plot can be a Matplotlib figure or a file path to an image.
    """
    pdf_path = _resolve_output_path(output_path, payload)
    styles = getSampleStyleSheet()
    story = []
    if lang_code == "hi":
        font_name = _get_devanagari_font_name()
    else:
        font_name = "Helvetica"
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=70,
        rightMargin=70,
        topMargin=48,
        bottomMargin=48,
    )

    title_font = _get_cinzel_font_name()
    title_style = ParagraphStyle(
        "TitleCinzel",
        parent=styles["Title"],
        fontName=title_font,
    )
    title = f"Report Timeline For - {payload.name}"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))
    timePeriod_text = "1 Year" if payload.timePeriod == '1Y' else "6 Months" if payload.timePeriod == '6M' else "1 Week" if payload.timePeriod == '1W' else "1 Day" if payload.timePeriod == '1D' else payload.timePeriod
    meta_lines = [
        f"Date of Birth: {payload.dateOfBirth}  |  Time of Birth: {payload.timeOfBirth}  |  Place of Birth: {payload.placeOfBirth}",
        f"Time Zone: {payload.timeZone}   | Period: {timePeriod_text}  |  Report Start: {payload.reportStartDate}"
    ]
    meta_style = ParagraphStyle(
        "MetaCenter",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName=font_name,
    )
    story.append(Paragraph("<br/>".join(meta_lines), meta_style))
    story.append(Spacer(1, 24))
    
    image_path = _resolve_plot_image(timeline_plot)
    if image_path:
        img = Image(image_path)
        max_width = doc.width
        max_height = doc.height * 0.75
        if img.drawWidth > 0 and img.drawHeight > 0:
            scale = min(max_width / img.drawWidth, max_height / img.drawHeight, 1.0)
            img.drawWidth = img.drawWidth * scale
            img.drawHeight = img.drawHeight * scale
        story.append(img)
        story.append(Spacer(1, 24))
    
    # Add the page break after the image
    story.append(PageBreak())

    if timeline_description:
        body_style = ParagraphStyle(
            "BodyJustified",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontName=font_name,
        )
        blocks = [b.strip() for b in timeline_description.split("\n\n") if b.strip()]
        for block in blocks:
            safe_text = block.replace("\n", "<br/>")
            story.append(KeepTogether([Paragraph(safe_text, body_style), Spacer(1, 8)]))

    if ai_summary:
        story.append(PageBreak())
        story.extend(_format_ai_summary(ai_summary, font_name))

    doc.build(story)
    return pdf_path
