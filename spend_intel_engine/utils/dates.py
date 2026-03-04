from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator

from .numbers import clamp


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def daterange_inclusive(start: date, end: date) -> Iterator[date]:
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def proximity_factor(current: date, exact: date, span_len: int) -> float:
    denominator = max(1, span_len)
    distance = abs((current - exact).days)
    return clamp(1.0 - min(distance / denominator, 1.0), 0.0, 1.0)
