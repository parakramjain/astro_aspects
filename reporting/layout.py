from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from .config import ReportConfig
from .i18n import lang_for_text, t
from .normalize import fmt_date, parse_iso_datetime, to_local
from .styles import FONT_EN_BOLD, FONT_EN_REG, FONT_HI_BOLD, FONT_HI_REG, PALETTE


PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN_LEFT = 18 * mm
MARGIN_RIGHT = 18 * mm
MARGIN_TOP = 16 * mm
MARGIN_BOTTOM = 18 * mm

HEADER_H = 18 * mm
FOOTER_H = 12 * mm


@dataclass(frozen=True)
class LayoutContext:
    config: ReportConfig
    report_title: str
    date_range: str


class NumberedCanvas(Canvas):
    """Canvas that supports 'Page X of Y' by storing page states."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:  # noqa: D401
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count: int) -> None:
        # placeholder; actual drawing happens in onPage
        self._page_count = page_count


def build_doc(output_path: str, on_page: Callable[[Canvas, BaseDocTemplate], None]) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )

    frame = Frame(
        MARGIN_LEFT,
        MARGIN_BOTTOM + FOOTER_H,
        PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT,
        PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - HEADER_H - FOOTER_H,
        id="content",
        showBoundary=0,
    )

    template = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc.addPageTemplates([template])
    return doc


def make_header_footer_drawer(ctx: LayoutContext, generated_local_iso: str) -> Callable[[Canvas, BaseDocTemplate], None]:
    def _draw(c: Canvas, doc: BaseDocTemplate) -> None:
        c.saveState()

        lang = lang_for_text(ctx.config.language_mode)
        header_font = FONT_EN_BOLD if lang == "EN" else FONT_HI_BOLD
        footer_font = FONT_EN_REG if lang == "EN" else FONT_HI_REG

        # Header
        header_y_top = PAGE_HEIGHT - MARGIN_TOP
        header_y_bottom = header_y_top - HEADER_H

        c.setFillColor(PALETTE.text_primary)
        c.setFont(header_font, 10)

        c.drawString(MARGIN_LEFT, header_y_top - 12, ctx.report_title)
        c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, header_y_top - 12, ctx.date_range)

        c.setStrokeColor(PALETTE.divider)
        c.setLineWidth(0.5)
        c.line(MARGIN_LEFT, header_y_bottom, PAGE_WIDTH - MARGIN_RIGHT, header_y_bottom)

        # Footer
        footer_y_bottom = MARGIN_BOTTOM
        footer_y_top = footer_y_bottom + FOOTER_H

        c.setStrokeColor(PALETTE.divider)
        c.setLineWidth(0.5)
        c.line(MARGIN_LEFT, footer_y_top, PAGE_WIDTH - MARGIN_RIGHT, footer_y_top)

        c.setFillColor(PALETTE.muted)
        c.setFont(footer_font, 8)

        c.drawString(MARGIN_LEFT, footer_y_bottom + 4, f"{t('generated', lang)}: {generated_local_iso}")
        c.drawCentredString(PAGE_WIDTH / 2, footer_y_bottom + 4, t("confidentiality", lang))

        page_num = doc.page
        page_count = int(getattr(c, "_page_count", 0) or 0)
        if page_count:
            c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, footer_y_bottom + 4, f"{t('page', lang)} {page_num} of {page_count}")
        else:
            c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, footer_y_bottom + 4, f"{t('page', lang)} {page_num}")

        c.restoreState()

    return _draw


def report_title_key(report_type: str) -> str:
    return "cover_title_daily" if report_type == "DAILY" else "cover_title_weekly"


def date_range_label(report_start: str, tz_name: str, lang: str) -> str:
    dt = parse_iso_datetime(report_start)
    if not dt:
        return str(report_start)
    return fmt_date(to_local(dt, tz_name), lang)
