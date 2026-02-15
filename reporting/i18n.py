from __future__ import annotations

from typing import Dict, Literal

from .config import ReportConfig


LABELS: Dict[str, Dict[str, str]] = {
    "HI": {
        "report_title": "ज्योतिष रिपोर्ट",
        "cover_title_daily": "दैनिक ज्योतिष रिपोर्ट",
        "cover_title_weekly": "साप्ताहिक ज्योतिष रिपोर्ट",
        "executive_summary": "सारांश",
        "life_areas": "जीवन क्षेत्र",
        "timeline": "समयरेखा",
        "key_moments": "मुख्य क्षण",
        "milestones": "जीवन मील के पत्थर",
        "appendix": "परिशिष्ट",
        "name": "नाम",
        "dob": "जन्म तिथि",
        "pob": "जन्म स्थान",
        "report_period": "रिपोर्ट अवधि",
        "language": "भाषा",
        "generated": "निर्मित",
        "confidentiality": "केवल व्यक्तिगत मार्गदर्शन हेतु",
        "page": "पृष्ठ",
        "date": "तिथि",
        "other": "अन्य",
        "start": "प्रारंभ",
        "peak": "शिखर",
        "end": "समाप्त",
        "focus_today": "आज का फोकस",
        "caution": "सावधानी",
        "best_time": "श्रेष्ठ समय",
        "action": "कार्रवाई",
        "aspect": "अस्पेक्ट",
        "main_areas": "मुख्य क्षेत्र",
        "keywords": "कीवर्ड",
        "how_to_read": "रिपोर्ट कैसे पढ़ें",
        "more_details": "अधिक विवरण",
        "no_major_signals": "कोई मुख्य संकेत नहीं",
        "top_opportunity": "शीर्ष अवसर",
        "top_caution": "शीर्ष सावधानी",
        "top_action": "आज की कार्रवाई",
        "action_today": "आज की कार्रवाई",
        "areas_impacted": "प्रभावित क्षेत्र",
    },
    "EN": {
        "report_title": "Astrology Report",
        "cover_title_daily": "Daily Astrology Report",
        "cover_title_weekly": "Weekly Astrology Report",
        "executive_summary": "Executive Summary",
        "life_areas": "Life Areas",
        "timeline": "Timeline",
        "key_moments": "Key Moments",
        "milestones": "Life Milestones",
        "appendix": "Appendix",
        "name": "Name",
        "dob": "Date of Birth",
        "pob": "Place of Birth",
        "report_period": "Report Period",
        "language": "Language",
        "generated": "Generated",
        "confidentiality": "For personal guidance only",
        "page": "Page",
        "date": "Date",
        "other": "Other",
        "start": "Start",
        "peak": "Peak",
        "end": "End",
        "focus_today": "Focus Today",
        "caution": "Caution",
        "best_time": "Best Time",
        "action": "Action",
        "aspect": "Aspect",
        "main_areas": "Main Areas",
        "keywords": "Keywords",
        "how_to_read": "How to read this report",
        "more_details": "More details",
        "no_major_signals": "No major signals",
        "top_opportunity": "Top Opportunity",
        "top_caution": "Top Caution",
        "top_action": "Actionable Recommendation",
        "action_today": "Action today",
        "areas_impacted": "Areas impacted",
    },
}


def t(key: str, lang: str) -> str:
    lang = lang.upper()
    return LABELS.get(lang, LABELS["EN"]).get(key, key)


def lang_for_text(language_mode: str) -> Literal["HI", "EN"]:
    return "EN" if language_mode == "EN" else "HI"


def section_title(key: str, config: ReportConfig) -> str:
    if config.language_mode == "BILINGUAL":
        return f"{t(key, 'HI')} / {t(key, 'EN')}"
    return t(key, lang_for_text(config.language_mode))
