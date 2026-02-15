from __future__ import annotations

import json
from pathlib import Path

import pytest

from reporting.config import ReportConfig
from reporting.renderer import generate_report_pdf


def _fonts_present(cfg: ReportConfig) -> bool:
    fonts_dir = cfg.fonts_dir
    required = [
        fonts_dir / cfg.noto_sans_devanagari_regular,
        fonts_dir / cfg.noto_sans_devanagari_bold,
        fonts_dir / cfg.noto_sans_regular,
        fonts_dir / cfg.noto_sans_bold,
    ]
    return all(p.exists() for p in required)


def test_generate_pdf_smoke(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="HI", output_dir=tmp_path)
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    sample = {
        "input": {
            "name": "Amit",
            "dateOfBirth": "1982-08-16",
            "timeOfBirth": "16:00:00",
            "placeOfBirth": "Yavatmal, India",
            "timeZone": "Asia/Kolkata",
            "latitude": 20.32,
            "longitude": 78.13,
            "timePeriod": "1D",
            "reportStartDate": "2026-01-16",
        },
        "generatedAt": "2026-01-16T10:00:00Z",
        "dailyWeekly": {
            "shortSummary": {"hi": "आज ऊर्जा स्थिर है।", "en": "Energy is steady today."},
            "areas": {
                "career": {"hi": ["फोकस बनाए रखें"], "en": ["Stay focused"]},
                "relationships": {"hi": ["स्पष्ट संवाद करें"], "en": ["Communicate clearly"]},
                "money": {"hi": ["खर्च नियंत्रित रखें"], "en": ["Control spending"]},
                "health_adj": {"hi": ["नींद पर ध्यान दें"], "en": ["Prioritize sleep"]},
            },
        },
        "timeline": {
            "aiSummary": "",
            "items": [],
        },
        "lifeEvents": [],
    }

    pdf_path = generate_report_pdf(sample, cfg)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
