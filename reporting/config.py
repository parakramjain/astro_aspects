from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    """Configuration for PDF report generation."""

    report_type: Literal["DAILY", "WEEKLY"]
    language_mode: Literal["HI", "EN", "BILINGUAL"] = "HI"

    output_dir: Path = Path("./out")
    file_name_template: str = "{name}__{dob}__{report_type}__{start}.pdf"

    include_appendix: bool = True
    max_keywords: int = 10
    max_area_bullets: int = 5
    max_summary_chars: int = 800

    density: Literal["COMPACT", "STANDARD", "DETAILED"] = "STANDARD"
    max_timeline_cards: int = 8
    max_timeline_cards_standard: int = 16
    max_key_moments: int = 5
    max_milestones: int = 10
    milestone_window_days: int = 90
    hide_empty_items: bool = True
    max_summary_bullets: int = 5
    max_card_bullets: int = 3
    max_bullet_chars: int = 110
    locale_timezone: str = "America/Toronto"
    include_full_appendix: bool = False
    max_summary_chars: int = 800

    timezone: str = "America/Toronto"

    # Font configuration
    fonts_dir: Path = Path("reporting/fonts")
    noto_sans_devanagari_regular: str = "NotoSansDevanagari-Regular.ttf"
    noto_sans_devanagari_bold: str = "NotoSansDevanagari-Bold.ttf"
    noto_sans_regular: str = "NotoSans-Regular.ttf"
    noto_sans_bold: str = "NotoSans-Bold.ttf"

    # Optional explicit absolute font paths (override fonts_dir + names when provided)
    noto_sans_devanagari_regular_path: Optional[Path] = None
    noto_sans_devanagari_bold_path: Optional[Path] = None
    noto_sans_regular_path: Optional[Path] = None
    noto_sans_bold_path: Optional[Path] = None

    # Output naming inputs (defaults derived from json input)
    override_file_name: Optional[str] = Field(default=None, description="Optional explicit output file name")
