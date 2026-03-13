from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class Timeframe:
    start: dt.date
    end: dt.date


def _add_months(anchor: dt.date, months: int) -> dt.date:
    total = anchor.month - 1 + months
    year = anchor.year + total // 12
    month = total % 12 + 1
    day = min(anchor.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.date(year, month, day)


def resolve_timeframe(
    *,
    months: int | None,
    start_date: dt.date | None,
    end_date: dt.date | None,
    default_months: int,
) -> Timeframe:
    start = start_date or dt.date.today()
    if end_date is not None:
        end = end_date
    else:
        end = _add_months(start, months or default_months)
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    return Timeframe(start=start, end=end)


def iter_days(start: dt.date, end: dt.date):
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)
