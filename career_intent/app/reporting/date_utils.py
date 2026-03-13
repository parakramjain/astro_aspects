from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


OVERLAP_PRECEDENCE = "caution"


@dataclass(frozen=True)
class DayState:
    date: dt.date
    state: str
    label: str


def to_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def to_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_date(value: str | None) -> str:
    date_value = to_date(value)
    return date_value.strftime("%b %d, %Y") if date_value else "N/A"


def fmt_short_date(date_value: dt.date) -> str:
    return date_value.strftime("%b %d")


def fmt_datetime(value: str | None) -> str:
    parsed = to_datetime(value)
    if not parsed:
        return value.strip() if isinstance(value, str) and value.strip() else "N/A"
    return parsed.strftime("%b %d, %Y %H:%M %Z").strip()


def month_start(date_value: dt.date) -> dt.date:
    return dt.date(date_value.year, date_value.month, 1)


def next_month(date_value: dt.date) -> dt.date:
    if date_value.month == 12:
        return dt.date(date_value.year + 1, 1, 1)
    return dt.date(date_value.year, date_value.month + 1, 1)


def iter_months(start: dt.date, end: dt.date) -> List[dt.date]:
    months: List[dt.date] = []
    cursor = month_start(start)
    while cursor <= end:
        months.append(cursor)
        cursor = next_month(cursor)
    return months


def iter_days(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += dt.timedelta(days=1)


def clip_window(window: Dict, start: dt.date, end: dt.date) -> tuple[dt.date, dt.date] | None:
    w_start = to_date(str(window.get("start_date") or ""))
    w_end = to_date(str(window.get("end_date") or ""))
    if not w_start or not w_end:
        return None
    clip_start = max(start, w_start)
    clip_end = min(end, w_end)
    if clip_end < clip_start:
        return None
    return clip_start, clip_end


def resolve_reference_date(meta: Dict, timeframe_start: dt.date | None) -> dt.date:
    generated_at = str(meta.get("report_generated_at") or meta.get("generated_at") or "")
    parsed_dt = to_datetime(generated_at)
    if parsed_dt:
        return parsed_dt.date()
    if timeframe_start:
        return timeframe_start
    return dt.date.today()


def normalize_windows(windows_like: object) -> List[tuple[dt.date, dt.date]]:
    if isinstance(windows_like, dict):
        windows = [windows_like]
    elif isinstance(windows_like, list):
        windows = [w for w in windows_like if isinstance(w, dict)]
    else:
        windows = []

    normalized: List[tuple[dt.date, dt.date]] = []
    for window in windows:
        start = to_date(str(window.get("start_date") or ""))
        end = to_date(str(window.get("end_date") or ""))
        if start and end and end >= start:
            normalized.append((start, end))
    return normalized


def day_state(
    day: dt.date,
    opportunity_windows: List[tuple[dt.date, dt.date]],
    caution_windows: List[tuple[dt.date, dt.date]],
) -> DayState:
    in_opportunity = any(start <= day <= end for start, end in opportunity_windows)
    in_caution = any(start <= day <= end for start, end in caution_windows)
    if in_opportunity and in_caution:
        if OVERLAP_PRECEDENCE == "caution":
            return DayState(day, "caution", "Overlapping signals: caution takes precedence")
        return DayState(day, "opportunity", "Overlapping signals: opportunity takes precedence")
    if in_opportunity:
        return DayState(day, "opportunity", "Opportunity window day")
    if in_caution:
        return DayState(day, "caution", "Caution window day")
    return DayState(day, "neutral", "Neutral day")


def build_day_strip(
    timeframe_start: dt.date,
    timeframe_end: dt.date,
    opportunity_windows: List[tuple[dt.date, dt.date]],
    caution_windows: List[tuple[dt.date, dt.date]],
) -> List[DayState]:
    return [
        day_state(day, opportunity_windows=opportunity_windows, caution_windows=caution_windows)
        for day in iter_days(timeframe_start, timeframe_end)
    ]


def overlap_days(window_a: tuple[dt.date, dt.date] | None, window_b: tuple[dt.date, dt.date] | None) -> int:
    if not window_a or not window_b:
        return 0
    start = max(window_a[0], window_b[0])
    end = min(window_a[1], window_b[1])
    if end < start:
        return 0
    return (end - start).days + 1


def phase_countdown(
    phase: str,
    report_date: dt.date,
    start_date: dt.date | None,
    end_date: dt.date | None,
) -> str:
    if not start_date and phase != "caution":
        return "Timing details are unavailable for this phase."

    if phase == "prepare":
        if not start_date:
            return "Preparation window is available now."
        if report_date < start_date:
            days = (start_date - report_date).days
            return f"⏳ {days} days left to prepare before your window opens."
        if report_date <= (end_date or start_date):
            return "Preparation phase is already underway."
        return "Preparation phase has passed."

    if phase == "execute":
        if not start_date or not end_date:
            return "Execution timing is being refined."
        if report_date < start_date:
            days = (end_date - start_date).days + 1
            return f"🚀 {days} days available in this execution window."
        if start_date <= report_date <= end_date:
            days_left = (end_date - report_date).days + 1
            return f"🚀 This execution phase is active now — {days_left} days remaining."
        return "This execution phase has passed."

    if phase == "caution":
        if not start_date:
            return "No caution phase is scheduled in this timeframe."
        if report_date < start_date:
            return f"⚠️ Caution begins on {start_date.strftime('%b %d, %Y')}. Plan commitments carefully before then."
        if end_date and report_date <= end_date:
            return "⚠️ Caution phase is active now. Keep commitments tightly scoped."
        return "Caution phase has passed."

    return ""
