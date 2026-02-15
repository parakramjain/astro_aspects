from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pytz

from .config import ReportConfig

logger = logging.getLogger(__name__)


HI_MONTHS = {
    1: "जनवरी",
    2: "फ़रवरी",
    3: "मार्च",
    4: "अप्रैल",
    5: "मई",
    6: "जून",
    7: "जुलाई",
    8: "अगस्त",
    9: "सितंबर",
    10: "अक्टूबर",
    11: "नवंबर",
    12: "दिसंबर",
}


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    try:
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            d = date.fromisoformat(s)
            return datetime.combine(d, time.min).replace(tzinfo=pytz.UTC)
    except Exception:
        pass

    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt
    except Exception:
        return None


def parse_iso_date(value: Any) -> Optional[date]:
    dt = parse_iso_datetime(value)
    return dt.date() if dt else None


def format_date_hi(d: date) -> str:
    return f"{d.day} {HI_MONTHS.get(d.month, str(d.month))} {d.year}"


def to_local(dt: datetime, tz_name: str) -> datetime:
    tz = pytz.timezone(tz_name)
    return dt.astimezone(tz)


def fmt_date(dt: datetime, lang: str) -> str:
    d = dt.date()
    if lang.upper() == "HI":
        return format_date_hi(d)
    month = d.strftime("%b")
    return f"{d.day} {month} {d.year}"


def fmt_dt(dt: datetime, lang: str) -> str:
    d = fmt_date(dt, lang)
    t = dt.strftime("%I:%M %p").lstrip("0")
    return f"{d} {t}"


def safe_parse_stringified_dict(value: str) -> Any:
    s = value.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return value
    try:
        return ast.literal_eval(s)
    except Exception:
        return value


def normalize_life_event_description(value: Any) -> Any:
    """Normalize lifeEvents.description which may be a stringified dict."""
    if isinstance(value, str):
        parsed = safe_parse_stringified_dict(value)
        if isinstance(parsed, dict):
            return parsed
        return value
    return value


def _coerce_to_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split("\n") if v.strip()]
    return [str(value).strip()] if str(value).strip() else []


def get_lang_text(value: Any, preferred: str, fallback: str) -> str:
    """Extract localized text. Logs when fallback is used."""
    if value is None:
        return ""

    if isinstance(value, dict):
        primary_val = value.get(preferred.lower()) or value.get(preferred.upper())
        if isinstance(primary_val, str) and primary_val.strip():
            return primary_val.strip()
        if isinstance(primary_val, list) and primary_val:
            return "\n".join(str(x).strip() for x in primary_val if str(x).strip())

        fb_val = value.get(fallback.lower()) or value.get(fallback.upper())
        if isinstance(fb_val, str) and fb_val.strip():
            logger.warning(
                "language_fallback",
                extra={"preferred": preferred, "used": fallback},
            )
            return fb_val.strip()
        if isinstance(fb_val, list) and fb_val:
            logger.warning(
                "language_fallback",
                extra={"preferred": preferred, "used": fallback},
            )
            return "\n".join(str(x).strip() for x in fb_val if str(x).strip())

        # Nothing found
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def bilingual_text(value: Any) -> Tuple[str, str]:
    """Return (hi, en) where missing values are ""."""
    if isinstance(value, dict):
        hi = get_lang_text(value, preferred="hi", fallback="en")
        en = get_lang_text(value, preferred="en", fallback="hi")
        return hi, en

    s = get_lang_text(value, preferred="hi", fallback="en")
    return s, ""


def smart_no_orphan_last_word(text: str) -> str:
    """Reduce chance of orphan single-word final line by binding last 2 words."""
    parts = [p for p in text.split(" ") if p]
    if len(parts) < 3:
        return text
    # Replace last space with non-breaking space.
    return " ".join(parts[:-2] + [parts[-2] + "&nbsp;" + parts[-1]])


def pick_keywords(item: Any, config: ReportConfig) -> List[str]:
    kws = getattr(item, "keywords", None)
    if not isinstance(kws, dict):
        return []

    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"

    raw = kws.get(preferred) or kws.get(preferred.upper())
    if raw is None:
        raw = kws.get(fallback) or kws.get(fallback.upper())

    out = _coerce_to_str_list(raw)
    dedup: List[str] = []
    for k in out:
        if k not in dedup:
            dedup.append(k)
        if len(dedup) >= config.max_keywords:
            break
    return dedup


def aspect_is_positive(aspect_nature: Optional[str]) -> bool:
    if not aspect_nature:
        return False
    s = str(aspect_nature).strip().lower()
    return s == "positive"


def aspect_is_challenging(aspect_nature: Optional[str]) -> bool:
    if not aspect_nature:
        return False
    s = str(aspect_nature).strip().lower()
    return s == "negative" or s == "challenging"


@dataclass(frozen=True)
class ExecutiveDerivation:
    focus: str
    caution: str
    best_time: str


def derive_executive_fields(timeline_items: Sequence[Any], report_start: Optional[date], config: ReportConfig) -> ExecutiveDerivation:
    """Deterministic derivations documented in code:

    - Focus: first 1–2 unique keywords from earliest positive items.
    - Caution: first keyword (or aspect) from earliest challenging item.
    - Best time: earliest exactDate on/after report_start (else earliest overall).
    """

    def _item_exact(it: Any) -> Optional[date]:
        return parse_iso_date(getattr(it, "exactDate", None))

    sorted_items = sorted(
        [it for it in timeline_items if getattr(it, "exactDate", None)],
        key=lambda it: (parse_iso_date(getattr(it, "exactDate", None)) or date.max, getattr(it, "aspect", "")),
    )

    positives = [it for it in sorted_items if aspect_is_positive(getattr(it, "aspectNature", None))]
    negatives = [it for it in sorted_items if aspect_is_challenging(getattr(it, "aspectNature", None))]

    focus_kws: List[str] = []
    for it in positives:
        for kw in pick_keywords(it, config):
            if kw not in focus_kws:
                focus_kws.append(kw)
            if len(focus_kws) >= 2:
                break
        if len(focus_kws) >= 2:
            break
    focus = " • ".join(focus_kws) if focus_kws else ""

    caution = ""
    if negatives:
        kw = pick_keywords(negatives[0], config)
        caution = kw[0] if kw else str(getattr(negatives[0], "aspect", "")).strip()

    best_item: Optional[Any] = None
    if report_start:
        future = [it for it in sorted_items if (_item_exact(it) and _item_exact(it) >= report_start)]
        best_item = future[0] if future else (sorted_items[0] if sorted_items else None)
    else:
        best_item = sorted_items[0] if sorted_items else None

    best_time = ""
    if best_item is not None:
        lang = "EN" if config.language_mode == "EN" else "HI"
        sd = parse_iso_datetime(getattr(best_item, "startDate", None))
        ed = parse_iso_datetime(getattr(best_item, "endDate", None))
        xd = parse_iso_datetime(getattr(best_item, "exactDate", None))
        if sd and ed and xd:
            sd = to_local(sd, config.locale_timezone)
            ed = to_local(ed, config.locale_timezone)
            xd = to_local(xd, config.locale_timezone)
            best_time = f"{fmt_date(sd, lang)} – {fmt_date(ed, lang)} ({fmt_date(xd, lang)})"

    return ExecutiveDerivation(
        focus=focus,
        caution=caution,
        best_time=best_time,
    )
