from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def to_int_score(value: float, low: int = 0, high: int = 100) -> int:
    return int(round(clamp(value, low, high)))
