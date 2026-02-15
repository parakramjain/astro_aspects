from __future__ import annotations

from typing import Dict

from reportlab.platypus import Paragraph, Table, TableStyle

from .styles import PALETTE


def section_header(title: str, styles: Dict[str, any]) -> Table:
    """Create a consistent section header with an accent strip."""

    tbl = Table([[Paragraph(title, styles["section"]) ]], colWidths=[None])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE.section_bg),
                ("LINEBEFORE", (0, 0), (0, -1), 4, PALETTE.accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl
