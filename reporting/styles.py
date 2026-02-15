from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .config import ReportConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Palette:
    text_primary: colors.Color
    text_secondary: colors.Color
    muted: colors.Color
    divider: colors.Color
    accent: colors.Color
    accent_light: colors.Color
    warning: colors.Color
    success: colors.Color

    cover_card_bg: colors.Color
    summary_bg: colors.Color
    section_bg: colors.Color
    card_bg: colors.Color

    badge_positive_bg: colors.Color
    badge_challenging_bg: colors.Color
    badge_neutral_bg: colors.Color


PALETTE = Palette(
    text_primary=colors.HexColor("#111111"),
    text_secondary=colors.HexColor("#444444"),
    muted=colors.HexColor("#666666"),
    divider=colors.HexColor("#DDDDDD"),
    accent=colors.HexColor("#1F4E79"),
    accent_light=colors.HexColor("#E7EFFB"),
    warning=colors.HexColor("#B54708"),
    success=colors.HexColor("#067647"),
    # Background fills specified by the report spec
    cover_card_bg=colors.HexColor("#F7F7F7"),
    summary_bg=colors.HexColor("#EEF3FF"),
    section_bg=colors.HexColor("#F7FAFF"),
    card_bg=colors.HexColor("#FAFAFA"),
    # Badge background fills specified by the report spec
    badge_positive_bg=colors.HexColor("#E8F5E9"),
    badge_challenging_bg=colors.HexColor("#FFF4E5"),
    badge_neutral_bg=colors.HexColor("#F2F4F7"),
)


FONT_HI_REG = "NotoSansDevanagari"
FONT_HI_BOLD = "NotoSansDevanagari-Bold"
FONT_EN_REG = "NotoSans"
FONT_EN_BOLD = "NotoSans-Bold"


def _resolve_font_path(fonts_dir: Path, file_name: str, override: Path | None) -> Path:
    if override is not None:
        return override
    return fonts_dir / file_name


def register_fonts(config: ReportConfig) -> None:
    """Register required fonts. Raises a clear error if fonts are missing."""

    fonts_dir = config.fonts_dir
    paths = {
        FONT_HI_REG: _resolve_font_path(fonts_dir, config.noto_sans_devanagari_regular, config.noto_sans_devanagari_regular_path),
        FONT_HI_BOLD: _resolve_font_path(fonts_dir, config.noto_sans_devanagari_bold, config.noto_sans_devanagari_bold_path),
        FONT_EN_REG: _resolve_font_path(fonts_dir, config.noto_sans_regular, config.noto_sans_regular_path),
        FONT_EN_BOLD: _resolve_font_path(fonts_dir, config.noto_sans_bold, config.noto_sans_bold_path),
    }

    missing = [str(p) for p in paths.values() if not Path(p).exists()]
    if missing:
        msg = (
            "Required font files not found.\n"
            "Please add the following .ttf files under reporting/fonts/ (or set *\"*_path\" config fields):\n"
            f"- {config.noto_sans_devanagari_regular}\n"
            f"- {config.noto_sans_devanagari_bold}\n"
            f"- {config.noto_sans_regular}\n"
            f"- {config.noto_sans_bold}\n"
            f"Missing paths:\n- " + "\n- ".join(missing)
        )
        raise FileNotFoundError(msg)

    for font_name, path in paths.items():
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(path)))


def build_styles(config: ReportConfig) -> Dict[str, ParagraphStyle]:
    base: StyleSheet1 = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=base["Normal"],
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        fontSize=26,
        leading=32,
        textColor=PALETTE.text_primary,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    cover_subtitle = ParagraphStyle(
        "CoverSubtitle",
        parent=base["Normal"],
        fontName=FONT_HI_REG if config.language_mode != "EN" else FONT_EN_REG,
        fontSize=12,
        leading=15,
        textColor=PALETTE.text_secondary,
        spaceAfter=12,
    )

    title = ParagraphStyle(
        "Title",
        parent=base["Normal"],
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        fontSize=22,
        leading=26,
        textColor=PALETTE.text_primary,
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    section = ParagraphStyle(
        "SectionHeader",
        parent=base["Normal"],
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        fontSize=13.5,
        leading=17,
        textColor=PALETTE.text_primary,
        spaceBefore=0,
        spaceAfter=0,
    )

    subheader = ParagraphStyle(
        "Subheader",
        parent=base["Normal"],
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        fontSize=11,
        leading=14,
        textColor=PALETTE.text_primary,
        spaceAfter=3,
    )

    body = ParagraphStyle(
        "Body",
        parent=base["Normal"],
        fontName=FONT_HI_REG if config.language_mode != "EN" else FONT_EN_REG,
        fontSize=10.2,
        leading=14,
        textColor=PALETTE.text_primary,
    )

    body_lead = ParagraphStyle(
        "BodyLead",
        parent=body,
        fontSize=11,
        leading=15,
    )

    label = ParagraphStyle(
        "Label",
        parent=base["Normal"],
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        fontSize=9.5,
        leading=12,
        textColor=PALETTE.text_secondary,
    )

    value = ParagraphStyle(
        "Value",
        parent=body,
        fontSize=10.5,
        leading=14,
    )

    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=body,
        textColor=PALETTE.muted,
    )

    small = ParagraphStyle(
        "Small",
        parent=base["Normal"],
        fontName=FONT_HI_REG if config.language_mode != "EN" else FONT_EN_REG,
        fontSize=8.5,
        leading=11,
        textColor=PALETTE.muted,
    )

    badge = ParagraphStyle(
        "Badge",
        parent=small,
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        textColor=PALETTE.text_secondary,
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=small,
        fontName=FONT_HI_BOLD if config.language_mode != "EN" else FONT_EN_BOLD,
        textColor=colors.white,
    )

    small_en = ParagraphStyle(
        "SmallEN",
        parent=small,
        fontName=FONT_EN_REG,
        textColor=PALETTE.muted,
    )

    return {
        "cover_title": cover_title,
        "cover_subtitle": cover_subtitle,
        "title": title,
        "section": section,
        "subheader": subheader,
        "body": body,
        "body_lead": body_lead,
        "label": label,
        "value": value,
        "body_muted": body_muted,
        "small": small,
        "badge": badge,
        "table_header": table_header,
        "small_en": small_en,
    }
