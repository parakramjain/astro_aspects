from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from reporting.config import ReportConfig
from reporting.i18n import t
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


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _sample_json(timeline_items: list[dict] | None = None) -> dict:
    return {
        "input": {
            "name": "Amit",
            "dateOfBirth": "1982-08-16",
            "timeOfBirth": "16:00:00",
            "placeOfBirth": "Yavatmal, India",
            "timeZone": "Asia/Kolkata",
            "latitude": 20.32,
            "longitude": 78.13,
            "timePeriod": "1D",
            "reportStartDate": "2026-01-16T00:00:00+00:00",
        },
        "generatedAt": "2026-01-16T10:00:00+00:00",
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
            "items": timeline_items or [],
        },
        "lifeEvents": [],
    }


def test_i18n_titles_language_mode(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="EN", output_dir=tmp_path, density="COMPACT")
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    sample = _sample_json(
        timeline_items=[
            {
                "aspect": "Sun trine Moon",
                "aspectNature": "positive",
                "startDate": "2026-01-16T08:00:00+00:00",
                "exactDate": "2026-01-16T12:00:00+00:00",
                "endDate": "2026-01-16T18:00:00+00:00",
                "description": {"en": "Clear momentum for goals.", "hi": "लक्ष्यों के लिए स्पष्ट गति।"},
                "keyPoints": {"exact": {"en": ["Follow through"], "hi": ["पूरा करें"]}},
                "facetsPoints": {"career": {"en": "Good focus", "hi": "अच्छा फोकस"}},
                "keywords": {"en": ["Momentum"], "hi": ["गति"]},
            }
        ]
    )

    pdf_path = generate_report_pdf(sample, cfg)
    text = _extract_text(pdf_path)
    assert t("executive_summary", "EN") in text
    assert t("executive_summary", "HI") not in text
    assert t("life_areas", "EN") in text


def test_compact_page_count_daily_smoke(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="EN", output_dir=tmp_path, density="COMPACT")
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    items = []
    for i in range(20):
        items.append(
            {
                "aspect": f"Aspect {i}",
                "aspectNature": "positive" if i % 2 == 0 else "negative",
                "startDate": "2026-01-16T08:00:00+00:00",
                "exactDate": f"2026-01-16T{8 + (i % 10):02d}:00:00+00:00",
                "endDate": "2026-01-16T18:00:00+00:00",
                "description": {"en": f"Headline {i}.", "hi": f"शीर्षक {i}."},
                "keyPoints": {"exact": {"en": ["Action"], "hi": ["कार्रवाई"]}},
                "facetsPoints": {"career": {"en": "Focus", "hi": "फोकस"}},
                "keywords": {"en": ["Focus"], "hi": ["फोकस"]},
            }
        )

    sample = _sample_json(timeline_items=items)
    pdf_path = generate_report_pdf(sample, cfg)
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) <= 12


def test_skip_empty_timeline_items(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="EN", output_dir=tmp_path, density="COMPACT")
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    items = [
        {
            "aspect": "Empty Aspect",
            "aspectNature": "neutral",
            "startDate": "2026-01-16T08:00:00+00:00",
            "exactDate": "2026-01-16T12:00:00+00:00",
            "endDate": "2026-01-16T18:00:00+00:00",
            "description": "—",
            "keyPoints": {},
            "facetsPoints": {},
            "keywords": {},
        },
        {
            "aspect": "Meaningful Aspect",
            "aspectNature": "positive",
            "startDate": "2026-01-16T09:00:00+00:00",
            "exactDate": "2026-01-16T13:00:00+00:00",
            "endDate": "2026-01-16T19:00:00+00:00",
            "description": {"en": "Strong support today.", "hi": "आज मजबूत समर्थन।"},
            "keyPoints": {"exact": {"en": ["Proceed"], "hi": ["आगे बढ़ें"]}},
            "facetsPoints": {"career": {"en": "Support", "hi": "समर्थन"}},
            "keywords": {"en": ["Support"], "hi": ["समर्थन"]},
        },
    ]

    sample = _sample_json(timeline_items=items)
    pdf_path = generate_report_pdf(sample, cfg)
    text = _extract_text(pdf_path)
    assert "Meaningful Aspect" in text
    assert "Empty Aspect" not in text


def test_datetime_formatting_local(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="EN", output_dir=tmp_path, density="COMPACT")
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    items = [
        {
            "aspect": "Time Test",
            "aspectNature": "positive",
            "startDate": "2026-01-16T08:00:00+00:00",
            "exactDate": "2026-01-16T12:00:00+00:00",
            "endDate": "2026-01-16T18:00:00+00:00",
            "description": {"en": "Timing check.", "hi": "समय जांच।"},
            "keyPoints": {"exact": {"en": ["Do it"], "hi": ["करें"]}},
            "facetsPoints": {"career": {"en": "Focus", "hi": "फोकस"}},
            "keywords": {"en": ["Time"], "hi": ["समय"]},
        }
    ]

    sample = _sample_json(timeline_items=items)
    pdf_path = generate_report_pdf(sample, cfg)
    text = _extract_text(pdf_path)
    assert "+00:00" not in text


def test_cover_title_single_occurrence(tmp_path: Path):
    cfg = ReportConfig(report_type="DAILY", language_mode="EN", output_dir=tmp_path, density="COMPACT")
    if not _fonts_present(cfg):
        pytest.skip("Required Noto fonts not found under reporting/fonts")

    sample = _sample_json(
        timeline_items=[
            {
                "aspect": "Sun trine Moon",
                "aspectNature": "positive",
                "startDate": "2026-01-16T08:00:00+00:00",
                "exactDate": "2026-01-16T12:00:00+00:00",
                "endDate": "2026-01-16T18:00:00+00:00",
                "description": {"en": "Clear momentum for goals.", "hi": "लक्ष्यों के लिए स्पष्ट गति।"},
                "keyPoints": {"exact": {"en": ["Follow through"], "hi": ["पूरा करें"]}},
                "facetsPoints": {"career": {"en": "Good focus", "hi": "अच्छा फोकस"}},
                "keywords": {"en": ["Momentum"], "hi": ["गति"]},
            }
        ]
    )

    pdf_path = generate_report_pdf(sample, cfg)
    reader = PdfReader(str(pdf_path))
    label = t("report_period", "EN")
    pages_with_label = sum(1 for page in reader.pages if label in (page.extract_text() or ""))
    assert pages_with_label == 1
