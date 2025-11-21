# Various astro services which can be offered using astro_core calculations.
# 1. Calculate the aspect_dict for a given birth details and prediction window.
# 2. 

from typing import Dict, List, Tuple, Optional
import datetime as dt
import pandas as pd

from astro_core.astro_core import (
    calc_aspect_periods,
    ASPECTS,
    ASPECT_ORB_DEG,
    TRANSIT_ORB_BY_PID,
    effective_orb,
)

# expects you already have:
# - calc_aspect_periods(...)  # HH:MM precise version from earlier
# - ASPECTS, ASPECT_ORB_DEG, TRANSIT_ORB_BY_PID, effective_orb, etc.

HARMONIC_ASPECTS = {"Con", "Sxt", "Tri"}   # generally benefic
CHALLENGE_ASPECTS = {"Sqr", "Opp"}         # generally challenging
MALEFICS = {"Sat", "Plu", "Mar"}           # tweak to your doctrine

# Normalize transit planet codes; SwissEphem short names are 3 letters
CANON = {
    "Sun": "Sun", "Moo": "Moo", "Mer": "Mer", "Ven": "Ven", "Mar": "Mar",
    "Jup": "Jup", "Sat": "Sat", "Ura": "Ura", "Nep": "Nep", "Plu": "Plu",
    "Moon": "Moo", "Jupiter": "Jup", "Saturn": "Sat", "Neptune": "Nep",
    "Uranus": "Ura", "Pluto": "Plu", "Mars": "Mar", "Mercury": "Mer", "Venus": "Ven",
}

def _canon_planet(p: str) -> str:
    return CANON.get(p, p[:3])

def _prediction_exclusions(period: str) -> List[str]:
    """Transit planets to exclude, canonicalized to 3-letter codes."""
    if period == "1 year":
        raw = ["Moo", "Mer", "Ven", "Sun", "Mar"]
    elif period == "6 months":
        raw = ["Moo", "Mer", "Ven", "Sun"]
    elif period == "1 month":
        raw = ["Moon"]  # normalize below
    else:
        raw = []
    return [_canon_planet(x) for x in raw]

def _fmt(dt_obj: dt.datetime) -> str:
    # transit_tz-aware datetime → 'YYYY-MM-DD HH:MM'
    return dt_obj.strftime("%Y-%m-%d %H:%M")

def _color_for(aspect_code: str, transit_short: str, natal_short: str) -> str:
    """
    Simple coloring rule:
      - Con/Sxt/Tri → green (except some malefic Conjunctions set to red)
      - Sqr/Opp → red
    You can evolve this with dignities/house weights later.
    """
    if aspect_code in CHALLENGE_ASPECTS:
        return "red"
    if aspect_code == "Con" and transit_short == "Sun" and natal_short in {"Sat", "Plu"}:
        return "red"
    return "green" if aspect_code in HARMONIC_ASPECTS else "red"

def build_aspect_dict(
    name: str,
    birth_date,                 # 'YYYY-MM-DD' | datetime.date | datetime.datetime
    birth_time: Optional[str],  # 'HH:MM' or 'HH:MM:SS' or None
    start_date,                 # same date formats
    end_date,                   # same date formats
    prediction_period: str,     # '1 year' | '6 months' | '1 month' | ...
    *,
    birth_tz: str = "Asia/Kolkata",
    transit_tz: str = "America/Toronto",
    sample_step_hours: int = 3,
) -> Dict[str, List[List]]:
    """
    Returns:
      {
        "Tran-Aspect-Nat": [
           [[start_str, end_str], color, exact_str],
           ...
        ],
        ...
      }

    Where start/end/exact are 'YYYY-MM-DD HH:MM' in transit_tz.
    """
    # Compute periods with HH:MM precision using your new core
    periods = calc_aspect_periods(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_tz=birth_tz,
        start_date=start_date,
        end_date=end_date,
        transit_tz=transit_tz,
        sample_step_hours=sample_step_hours,
    )

    # Exclusions based on requested horizon
    exclude_transit = set(_prediction_exclusions(prediction_period))

    # Build flattened, sorted list (keeps your previous structure idea)
    rows: List[List] = []
    for p in periods:
        t_short, a_code, n_short = p.aspect
        t_short_c = _canon_planet(t_short)
        n_short_c = _canon_planet(n_short)

        if t_short_c in exclude_transit:
            continue

        rows.append([
            _fmt(p.start_dt),           # start (local transit tz)
            _fmt(p.end_dt),             # end
            _fmt(p.exact_dt),           # exact
            (t_short_c, a_code, n_short_c),
            round(p.angle_diff_min, 6),
            round(p.angle_diff_min, 6), # keep a second field if you still expect angle_diff_360
        ])

    # sort by start time
    rows.sort(key=lambda r: pd.to_datetime(r[0]))

    # Fold to dict with color coding
    aspect_dict: Dict[str, List[List]] = {}
    for row in rows:
        start_s, end_s, exact_s, asp_tuple, ang_min, _ = row
        t_short_c, a_code, n_short_c = asp_tuple
        key = f"{t_short_c}-{a_code}-{n_short_c}"
        color = _color_for(a_code, t_short_c, n_short_c)
        payload = [[start_s, end_s], color, exact_s]

        aspect_dict.setdefault(key, []).append(payload)

    return aspect_dict

if __name__ == "__main__":
    # Example usage
    result = build_aspect_dict(
        name="Alice Example",
        birth_date="1990-05-15",
        birth_time="14:30",
        start_date="2024-01-01",
        end_date="2024-12-31",
        prediction_period="6 months",
        birth_tz="Asia/Kolkata",
        transit_tz="America/Toronto"
    )
    for k, v in result.items():
        print(f"{k}:")
        for entry in v:
            print(f"  {entry}")
    
    # print(result)