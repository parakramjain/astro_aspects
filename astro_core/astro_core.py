"""astro_core
================================================================================
Core astronomy / astrology computation utilities for the project.

Purpose
-------
Provides centralized configuration of ayanamsha (sidereal reference), Swiss
Ephemeris flag management, planetary longitude calculation, aspect detection
between natal and transit positions, and higher-level aspect period extraction.

Public API (stable)
-------------------
set_ayanamsha(mode, name, custom_offset) -> None
    Configure global sidereal/tropical mode and (optionally) custom offset.
get_flags() -> int
    Obtain the Swiss Ephemeris flags honoring current sidereal/tropical mode.
current_ayanamsha_info() -> dict
    Inspect current ayanamsha configuration.
calc_planet_pos(date, time, tz_str, ...) -> dict[int, float]
    Planetary ecliptic longitudes (deg) for Sun..Pluto at given local datetime.
find_aspects(natal_positions, transit_positions, ...) -> list[AspectHit]
    Instantaneous aspects between two position maps.
calc_aspect_periods(birth_date, birth_time, birth_tz, start_date, end_date, ...) -> list[AspectPeriod]
    Time-bounded windows for each detected transit-to-natal aspect including
    refined exact moments and min angle separation.

Data Structures
---------------
AspectHit:
    Single instant where a transit planet falls within orb to a natal planet
    for a given aspect (Con/Sxt/Sqr/Tri/Opp).
AspectPeriod:
    Start, exact, and end timestamps (timezone-aware) for a continuous aspect
    window plus angle difference metadata.

Key Concepts
------------
"Ayanamsha" : Angular offset used to convert tropical zodiac to sidereal.
"Orb"       : Maximum angular distance (deg) allowing an aspect to be considered active.
"Aspect"    : Specific angular relationship (0,60,90,120,180 deg) between two bodies.

Dependencies
------------
Python >= 3.11, swisseph, zoneinfo (standard library, PEP 615).

Performance Notes
-----------------
calc_aspect_periods performs coarse sampling (default 6h) then a two-stage
refinement (15 min grid + 1 min zoom) around provisional exact times for good
precision while controlling CPU usage.

Thread Safety
-------------
Module-level ayanamsha configuration is global and NOT thread-safe. For
concurrent differing ayanamsha requirements, isolate processes or refactor
state handling.

Example
-------
from astro_core import calc_aspect_periods
periods = calc_aspect_periods("1990-01-01", "12:00", "Asia/Kolkata", "2025-01-01", "2025-01-05")
for p in periods:
    print(p.aspect, p.start_dt, p.exact_dt, p.end_dt)

Metadata
--------
Author: Parakram (inferred from workspace path)
Version: 1.0.0
Last Revision Date: 2025-11-07
Copyright: © 2025 Parakram. All rights reserved.
License: (Add chosen license here, e.g. MIT / Proprietary)
History:
    1.0.0 (2025-11-07) Initial documented header added; existing computational
                        logic retained.

"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional
from zoneinfo import ZoneInfo

try:
    import swisseph as swe
except Exception as e:  # ModuleNotFoundError or other import errors
    raise ImportError(
        "Swiss Ephemeris (pyswisseph) is required. Install with: pip install pyswisseph\n"
        f"Original import error: {e}"
    )

# --- Swiss Ephemeris setup ---
swe.set_ephe_path("")  # put your path if you ship SE files locally

# ---------------- Ayanamsha config (centralized) ----------------
# Friendly-name → Swiss Ephemeris constant NAME mapping (resolved at runtime)
AYANAMSHA_MAP = {
    "Lahiri": "SIDM_LAHIRI",
    "Raman": "SIDM_RAMAN",
    "Krishnamurti": "SIDM_KRISHNAMURTI",
    "FaganBradley": "SIDM_FAGAN_BRADLEY",
    "DeLuce": "SIDM_DELUCE",
    # Yukteshwar constant is spelled 'SIDM_YUKTESHWAR' in many builds
    "Yukteshwar": "SIDM_YUKTESHWAR",
    "Sassanian": "SIDM_SASSANIAN",
    # Galactic center zero Sagittarius; name varies across versions; we try this first
    "GalacticCenter": "SIDM_GALCENT_0SAG",
    "Tropical": None,  # clarity
    "USER": "USER",
}

def _resolve_sidm_const(const_name: str | None):
    """Return the integer SIDM_* constant value from swisseph by name, or None.
    Tries a couple of common variant names when necessary and falls back to None.
    """
    if not const_name:
        return None
    const = getattr(swe, const_name, None)
    if const is not None:
        return const
    # Try common alias for Yukteshwar
    if const_name == "SIDM_YUKTESHVARA":
        const = getattr(swe, "SIDM_YUKTESHWAR", None)
        if const is not None:
            return const
    if const_name == "SIDM_YUKTESHWAR":
        const = getattr(swe, "SIDM_YUKTESHVARA", None)
        if const is not None:
            return const
    # Try some alternative galactic center naming if present
    if const_name == "SIDM_GALCENT_0SAG":
        # Some builds expose SIDM_GALCENTIC or similar — scan for GALCENT
        for name in dir(swe):
            if name.startswith("SIDM_") and "GAL" in name.upper():
                return getattr(swe, name)
    return None

# Module-level state
_AYAN_MODE: str = "sidereal"          # "sidereal" | "tropical"
_AYAN_NAME: str = "Lahiri"            # Only meaningful in sidereal mode
_AYAN_CUSTOM: float | None = None      # Only used when name == "USER"
SIDEREAL_ENABLED: bool = True          # convenience boolean

def set_ayanamsha(
    ayanamsha_mode: str = "sidereal",
    ayanamsha_name: str = "Lahiri",
    ayanamsha_custom_offset_deg: float | None = None,
) -> None:
    """
    Configure ayanamsha globally for subsequent calculations.

    - If mode == "tropical": disable sidereal; do not pass FLG_SIDEREAL and
      reset Swiss Ephemeris sidereal mode by calling set_sid_mode(0).
    - If mode == "sidereal" and name != "USER": set Swiss to the mapped constant.
    - If mode == "sidereal" and name == "USER": set Swiss with custom offset.
    """
    global _AYAN_MODE, _AYAN_NAME, _AYAN_CUSTOM, SIDEREAL_ENABLED

    mode = (ayanamsha_mode or "sidereal").lower()
    name = ayanamsha_name

    if mode == "tropical":
        swe.set_sid_mode(0)  # disable sidereal corrections
        SIDEREAL_ENABLED = False
    else:
        # sidereal mode
        if name == "USER":
            # Use user-provided offset in degrees
            offs = float(ayanamsha_custom_offset_deg or 0.0)
            swe.set_sid_mode(swe.SIDM_USER, 0, offs)
        else:
            const_name = AYANAMSHA_MAP.get(name)
            const = _resolve_sidm_const(const_name)
            if const is None:
                # Fallback to Lahiri if name not found or mapped to Tropical/USER in sidereal branch
                const = _resolve_sidm_const("SIDM_LAHIRI")
                name = "Lahiri"
            swe.set_sid_mode(const)
        SIDEREAL_ENABLED = True

    _AYAN_MODE = mode
    _AYAN_NAME = name
    _AYAN_CUSTOM = ayanamsha_custom_offset_deg if name == "USER" and mode == "sidereal" else None

def get_flags() -> int:
    """
    Return Swiss Ephemeris flags with/without FLG_SIDEREAL depending on current mode.
    """
    base = swe.FLG_SWIEPH
    return base | swe.FLG_SIDEREAL if SIDEREAL_ENABLED else base

def current_ayanamsha_info() -> dict:
    return {
        "mode": _AYAN_MODE,
        "name": _AYAN_NAME,
        "custom_offset_deg": _AYAN_CUSTOM,
    }

# Backward-compatible default: behave as Sidereal Lahiri unless overridden
set_ayanamsha("sidereal", "Lahiri", None)

# --- Planets: Sun..Pluto (geocentric, ecliptic longitudes) ---
PLANET_IDS = list(range(swe.SUN, swe.PLUTO + 1))

# --- Planet short name mapping ---
PLANET_FULL_NAMES = {
            "Sun": "Sun",
            "Moo": "Moon",
            "Mer": "Mercury",
            "Ven": "Venus",
            "Mar": "Mars",
            "Jup": "Jupiter",
            "Sat": "Saturn",
            "Ura": "Uranus",
            "Nep": "Neptune",
            "Plu": "Pluto",
        }

# --- Major aspects ---
ASPECTS: Dict[int, str] = {
    0:   "Con",
    60:  "Sxt",
    90:  "Sqr",
    120: "Tri",
    180: "Opp",
}

# --- your per-transit-planet orbs (SwissEphem IDs: 0..9 = Sun..Pluto) ---
TRANSIT_ORB_BY_PID = {
    0: 2.0,  # Sun
    1: 3.0,  # Moon
    2: 2.0,  # Mercury
    3: 2.0,  # Venus
    4: 2.0,  # Mars
    5: 1.0,  # Jupiter
    6: 1.0,  # Saturn
    7: 1.0,  # Uranus
    8: 1.0,  # Neptune
    9: 1.0,  # Pluto
}

# Orbs keyed by aspect angle (degrees). Tweak as you prefer.
ASPECT_ORB_DEG: Dict[int, float] = {
    0:   4.0,   # Conjunction
    60:  3.0,   # Sextile
    90:  4.0,   # Square
    120: 4.0,   # Trine
    180: 4.0,   # Opposition
}

# Orbs keyed by aspect angle (degrees). Tweak as you prefer.
NATAL_ASPECT_ORB_DEG: Dict[int, float] = {
    0:   10.0,   # Conjunction
    60:  15.0,   # Sextile
    90:  15.0,   # Square
    120: 15.0,   # Trine
    180: 15.0,   # Opposition
}
# Note: Use get_flags() instead of hardcoded constants.

@dataclass
class AspectHit:
    natal_planet: str
    transit_planet: str
    aspect_code: str             # 'Con', 'Sxt', ...
    delta_deg: float             # absolute distance to the aspect angle
    exact_delta_deg: float       # same as delta_deg (kept for compatibility)
    timestamp: dt.datetime       # UTC timestamp used for the calculation
    is_applying: Optional[bool]  # None if unknown; else True/False

@dataclass
class AspectPeriod:
    start_dt: dt.datetime          # in transit_tz (timezone-aware)
    exact_dt: dt.datetime          # in transit_tz (timezone-aware)
    end_dt: dt.datetime            # in transit_tz (timezone-aware)
    aspect: Tuple[str, str, str]   # (TransitShort, AspectCode, NatalShort)
    angle_diff: float              # min delta at exact_dt (deg)
    angle_diff_360: float          # same value, kept for compatibility
    angle_diff_min: float          # same value

# ----------------- Time helpers -----------------
def _to_utc(dt_local: dt.datetime, tz: ZoneInfo) -> dt.datetime:
    """Attach tz if naive (assume given local tz), convert to UTC, return aware dt."""
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=tz)
    return dt_local.astimezone(dt.UTC)

def _julday_utc(dtu: dt.datetime) -> float:
    """Build UT Julian day from a UTC datetime (aware)."""
    if dtu.tzinfo is None:
        raise ValueError("UTC datetime must be timezone-aware")
    dtu_utc = dtu.astimezone(dt.UTC)
    frac_hour = dtu_utc.hour + dtu_utc.minute/60.0 + dtu_utc.second/3600.0 + dtu_utc.microsecond/3_600_000_000.0
    return swe.julday(dtu_utc.year, dtu_utc.month, dtu_utc.day, frac_hour)

def _parse_date(d: object) -> dt.date:
    if isinstance(d, dt.date) and not isinstance(d, dt.datetime):
        return d
    if isinstance(d, str):
        return dt.date.fromisoformat(d)
    if isinstance(d, dt.datetime):
        return d.date()
    raise TypeError("birth/start/end dates must be date, datetime, or 'YYYY-MM-DD' string")

def _parse_time(t: Optional[str]) -> Tuple[int, int, int]:
    if not t:
        return (0, 0, 0)
    parts = [int(x) for x in t.split(":")]
    if len(parts) == 2:
        h, m = parts; s = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError("time must be 'HH:MM' or 'HH:MM:SS'")
    return (h, m, s)

def format_dt(dt_obj):
        # dt_obj is timezone-aware in transit_tz
        return dt_obj.strftime("%Y-%m-%d %H:%M")

# --------------- Astronomy helpers ---------------
def effective_orb(
    aspect_angle: int,
    t_pid: int,
    *,
    aspect_orbs: Dict[int, float] = ASPECT_ORB_DEG,
    transit_orbs: Dict[int, float] = TRANSIT_ORB_BY_PID,
    default_aspect_orb: float = 1.0,
    default_transit_orb: float = 1.0,
) -> float:
    """Active orb = min(orb_by_aspect, orb_by_transit_planet)."""
    a_orb = aspect_orbs.get(aspect_angle, default_aspect_orb)
    t_orb = transit_orbs.get(t_pid, default_transit_orb)
    return max(a_orb, t_orb)

def _planet_longitudes_utc(
    dtu: dt.datetime,
    flags: Optional[int] = None,
    *,
    allowed_pids: Optional[List[int]] = None,
) -> Dict[int, float]:
    """Geocentric ecliptic longitudes (deg) for Sun..Pluto at a UTC datetime.

    If allowed_pids is provided, only compute those planet IDs; otherwise use PLANET_IDS.
    """
    jd_ut = _julday_utc(dtu)
    if flags is None:
        flags = get_flags()
    out: Dict[int, float] = {}
    pids = allowed_pids if allowed_pids is not None else PLANET_IDS
    for pid in pids:
        pos, _ = swe.calc_ut(jd_ut, pid, flags)
        out[pid] = pos[0]  # ecliptic longitude in degrees
    return out

def _delta_circ(a: float, b: float) -> float:
    """Minimum absolute circular distance between two angles in degrees [0..180]."""
    d = abs((a - b) % 360.0)
    return d if d <= 180.0 else 360.0 - d

def _dist_to_aspect(delta_deg: float, aspect_angle: int) -> float:
    """Distance of an angular separation to an aspect angle, circularly."""
    return _delta_circ(delta_deg, float(aspect_angle))

def _planet_name_short(pid: int) -> str:
    return swe.get_planet_name(pid)[:3]

# --------------- Public API ----------------------
def calc_planet_pos(
    date: dt.date | dt.datetime | str,
    time: Optional[str] = None,
    tz_str: str = "UTC",
    flags: Optional[int] = None,
    *,
    ayanamsha_mode: str | None = None,
    ayanamsha_name: str | None = None,
    ayanamsha_custom_offset_deg: float | None = None,
) -> Dict[int, float]:
    """
    Planetary longitudes for the given local date/time in tz_str.
    Returns {planet_id: ecliptic_longitude_deg}.
    """
    # Allow per-call override of ayanamsha (optional); otherwise use current module config
    if ayanamsha_mode:
        set_ayanamsha(
            ayanamsha_mode=ayanamsha_mode,
            ayanamsha_name=ayanamsha_name or _AYAN_NAME,
            ayanamsha_custom_offset_deg=ayanamsha_custom_offset_deg,
        )
    tz = ZoneInfo(tz_str)
    d = _parse_date(date)
    h, m, s = _parse_time(time)
    local_dt = dt.datetime(d.year, d.month, d.day, h, m, s)
    utc_dt = _to_utc(local_dt, tz)
    return _planet_longitudes_utc(utc_dt, flags=(flags if flags is not None else get_flags()))

def find_aspects(
    natal_positions: Dict[int, float],
    transit_positions: Dict[int, float],
    *,
    aspect_orbs: Dict[int, float] = ASPECT_ORB_DEG,
) -> List[AspectHit]:
    """
    Find aspects between natal (static) and transit (current) longitudes.
    Uses aspect_orbs keyed by aspect angle in degrees.
    """
    hits: List[AspectHit] = []
    for n_pid, n_lon in natal_positions.items():
        for t_pid, t_lon in transit_positions.items():
            # angle between longitudes (0..180 as separation)
            sep = _delta_circ(t_lon, n_lon)
            # print(f"Angle distance between {n_pid} and {t_pid}: {sep:.2f}°")
            for a_angle, a_code in ASPECTS.items():
                orb = effective_orb(a_angle, t_pid, aspect_orbs=aspect_orbs, transit_orbs=TRANSIT_ORB_BY_PID)
                dist = _dist_to_aspect(sep, a_angle)
                # print angle distance between planets
                # print(f"Angle distance between {n_pid} and {t_pid}: {dist:.2f}° and orb: {orb}° for aspect {a_code}")
                if dist <= orb:
                    # applying vs separating (heuristic): compare exactness if transit moves prograde.
                    # We can't know next value here, so set None; the period finder will resolve.
                    hits.append(
                        AspectHit(
                            natal_planet=_planet_name_short(n_pid),
                            transit_planet=_planet_name_short(t_pid),
                            aspect_code=a_code,
                            delta_deg=dist,
                            exact_delta_deg=dist,
                            timestamp=dt.datetime.now(dt.UTC),
                            is_applying=None,
                        )
                    )
    return hits
def _sep_deg_at_local_dt(
    local_dt: dt.datetime,
    tz_transit: ZoneInfo,
    t_pid: int,
    n_lon: float,
    aspect_angle: int,
    flags: Optional[int],
    *,
    allowed_pids: Optional[List[int]] = None,
) -> float:
    """Distance (deg) of t_pid to aspect_angle from natal n_lon at given local_dt."""
    utc_dt = _to_utc(local_dt, tz_transit)
    # compute only requested pid to avoid unnecessary work
    t_lon = _planet_longitudes_utc(
        utc_dt,
        flags=(flags if flags is not None else get_flags()),
        allowed_pids=[t_pid] if allowed_pids is None else allowed_pids,
    )[t_pid]
    sep = _delta_circ(t_lon, n_lon)
    return _dist_to_aspect(sep, aspect_angle)

def _refine_exact_time(
    coarse_best_dt: dt.datetime,
    tz_transit: ZoneInfo,
    t_pid: int,
    n_lon: float,
    aspect_angle: int,
    flags: Optional[int],
    coarse_window_hours: int = 6,
) -> Tuple[dt.datetime, float]:
    """
    Refine the moment of minimum distance within ±coarse_window_hours around coarse_best_dt.
    Stage 1: sample every 15 min; Stage 2: sample every 1 min in ±30 min of the best 15-min result.
    Returns (best_local_dt, best_dist_deg).
    """
    # Stage 1: 15-minute grid
    start1 = coarse_best_dt - dt.timedelta(hours=coarse_window_hours)
    end1   = coarse_best_dt + dt.timedelta(hours=coarse_window_hours)
    step1  = dt.timedelta(minutes=15)

    best_dt = start1
    best_d  = float("inf")
    cur = start1
    while cur <= end1:
        d = _sep_deg_at_local_dt(cur, tz_transit, t_pid, n_lon, aspect_angle, flags)
        if d < best_d:
            best_d = d
            best_dt = cur
        cur += step1

    # Stage 2: 1-minute zoom around best_dt (±30 minutes)
    start2 = best_dt - dt.timedelta(minutes=30)
    end2   = best_dt + dt.timedelta(minutes=30)
    step2  = dt.timedelta(minutes=1)

    cur = start2
    while cur <= end2:
        d = _sep_deg_at_local_dt(cur, tz_transit, t_pid, n_lon, aspect_angle, flags)
        if d < best_d:
            best_d = d
            best_dt = cur
        cur += step2

    return best_dt, best_d

def calc_aspect_periods(
    birth_date: dt.date | dt.datetime | str,
    birth_time: Optional[str],
    birth_tz: str,
    start_date: dt.date | dt.datetime | str,
    end_date: dt.date | dt.datetime | str,
    *,
    transit_tz: str = "UTC",
    sample_step_hours: int = 6,     # use 6h or 3h for better start/end timing
    flags: Optional[int] = None,
    aspect_orbs: Dict[int, float] = ASPECT_ORB_DEG,
    exclude_transit_short: Optional[Iterable[str]] = None,
) -> List[AspectPeriod]:
    # Natal longitudes at birth instant
    natal_pos = calc_planet_pos(
        birth_date, birth_time, tz_str=birth_tz,
        flags=(flags if flags is not None else get_flags())
    )

    sd = _parse_date(start_date)
    ed = _parse_date(end_date)
    if ed < sd:
        raise ValueError("end_date must be >= start_date")

    tz_transit = ZoneInfo(transit_tz)

    # Build allowed transit planet IDs after applying optional exclusions by 3-letter short code (e.g., 'Moo','Mer').
    allowed_transit_pids: Optional[List[int]] = None
    if exclude_transit_short:
        excl = {s[:3] for s in exclude_transit_short}
        allowed_transit_pids = [pid for pid in PLANET_IDS if _planet_name_short(pid) not in excl]

    # Iterate in local transit_tz
    current = dt.datetime(sd.year, sd.month, sd.day, 0, 0, 0, tzinfo=tz_transit)
    stop    = dt.datetime(ed.year, ed.month, ed.day, 23, 59, 59, tzinfo=tz_transit)

    # Track active aspect windows keyed by (Tshort, Acode, Nshort, t_pid, n_pid, a_angle)
    active: Dict[Tuple[str, str, str, int, int, int], Dict] = {}
    periods: List[AspectPeriod] = []

    while current <= stop:
        utc_dt = _to_utc(current, tz_transit)
        trans_pos = _planet_longitudes_utc(
            utc_dt,
            flags=(flags if flags is not None else get_flags()),
            allowed_pids=allowed_transit_pids,
        )

        touched: set = set()

        for n_pid, n_lon in natal_pos.items():
            n_short = _planet_name_short(n_pid)
            for t_pid, t_lon in trans_pos.items():
                t_short = _planet_name_short(t_pid)
                sep = _delta_circ(t_lon, n_lon)
                for a_angle, a_code in ASPECTS.items():
                    orb = effective_orb(a_angle, t_pid, aspect_orbs=aspect_orbs, transit_orbs=TRANSIT_ORB_BY_PID)
                    dist = _dist_to_aspect(sep, a_angle)
                    key = (t_short, a_code, n_short, t_pid, n_pid, a_angle)

                    if dist <= orb:
                        touched.add(key)
                        if key not in active:
                            active[key] = {
                                "start_dt": current,    # local
                                "last_dt": current,     # local
                                "min_dist": dist,
                                "min_dt": current,      # local
                            }
                        else:
                            st = active[key]
                            st["last_dt"] = current
                            if dist < st["min_dist"]:
                                st["min_dist"] = dist
                                st["min_dt"]   = current

        # Close any aspect keys not hit at this tick
        to_close = []
        for key, st in active.items():
            if key not in touched:
                to_close.append(key)

        for key in to_close:
            t_short, a_code, n_short, t_pid, n_pid, a_angle = key
            st = active.pop(key)

            # refine the exact time around st["min_dt"]
            exact_dt, exact_dist = _refine_exact_time(
                st["min_dt"],
                tz_transit,
                t_pid=t_pid,
                n_lon=natal_pos[n_pid],
                aspect_angle=a_angle,
                flags=flags,
                coarse_window_hours=max(sample_step_hours, 3),
            )

            periods.append(
                AspectPeriod(
                    start_dt=st["start_dt"],
                    exact_dt=exact_dt,
                    end_dt=st["last_dt"],
                    aspect=(t_short, a_code, n_short),
                    angle_diff=exact_dist,
                    angle_diff_360=exact_dist,
                    angle_diff_min=exact_dist,
                )
            )

        current += dt.timedelta(hours=sample_step_hours)

    # Flush still-active windows at loop end
    for key, st in active.items():
        t_short, a_code, n_short, t_pid, n_pid, a_angle = key
        exact_dt, exact_dist = _refine_exact_time(
            st["min_dt"],
            tz_transit,
            t_pid=t_pid,
            n_lon=natal_pos[n_pid],
            aspect_angle=a_angle,
            flags=flags,
            coarse_window_hours=max(sample_step_hours, 3),
        )
        periods.append(
            AspectPeriod(
                start_dt=st["start_dt"],
                exact_dt=exact_dt,
                end_dt=st["last_dt"],
                aspect=(t_short, a_code, n_short),
                angle_diff=exact_dist,
                angle_diff_360=exact_dist,
                angle_diff_min=exact_dist,
            )
        )

    # Optional: merge adjacent windows if they’re effectively continuous
    periods.sort(key=lambda p: (p.aspect, p.start_dt))
    merged: List[AspectPeriod] = []
    for p in periods:
        if (
            merged and
            merged[-1].aspect == p.aspect and
            (merged[-1].end_dt + dt.timedelta(hours=sample_step_hours)) >= p.start_dt
        ):
            prev = merged[-1]
            # choose the better exact (smaller angle)
            better = prev if prev.angle_diff_min <= p.angle_diff_min else p
            merged[-1] = AspectPeriod(
                start_dt=min(prev.start_dt, p.start_dt),
                exact_dt=better.exact_dt,
                end_dt=max(prev.end_dt, p.end_dt),
                aspect=prev.aspect,
                angle_diff=min(prev.angle_diff, p.angle_diff),
                angle_diff_360=min(prev.angle_diff_360, p.angle_diff_360),
                angle_diff_min=min(prev.angle_diff_min, p.angle_diff_min),
            )
        else:
            merged.append(p)
    return merged

# --------------------------- Validation hooks ---------------------------
def _selfcheck_ayanamsha() -> None:
    """Quick self-check that sidereal vs tropical differs as expected.

    Computes Sun longitude for a known date/time in UTC for both modes and prints
    the delta, which should be close to the ayanamsha (~22–24° depending on epoch).
    """
    test_dt = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=dt.UTC)

    set_ayanamsha("sidereal", "Lahiri", None)
    lon_sid = _planet_longitudes_utc(test_dt)[swe.SUN]

    set_ayanamsha("tropical", "Tropical", None)
    lon_trop = _planet_longitudes_utc(test_dt)[swe.SUN]

    delta = abs((lon_trop - lon_sid) % 360.0)
    if delta > 180:
        delta = 360.0 - delta
    info = current_ayanamsha_info()
    print("[selfcheck] Sidereal(Lahiri) vs Tropical Sun delta ≈", round(delta, 2), "deg; info:", info)

if __name__ == "__main__":
    # Example usage
    birth_date = "1990-01-01"
    birth_time = "12:00"
    birth_tz = "Asia/Kolkata"
    start_date = "2025-01-01"
    end_date = "2025-01-02"
    transit_tz="America/Toronto"
    # transit_tz="UTC"

    periods = calc_aspect_periods(
        birth_date,
        birth_time,
        birth_tz,
        start_date,
        end_date,
        transit_tz=transit_tz,
        sample_step_hours=1,
    )

    def format_dt(dt_obj):
        # dt_obj is timezone-aware in transit_tz
        return dt_obj.strftime("%Y-%m-%d %H:%M")
    
    def periods_to_rows(periods):
        """Return rows like your earlier structure but with HH:MM strings."""
        rows = []
        for p in periods:
            rows.append([
                p.start_dt,
                format_dt(p.exact_dt),
                format_dt(p.end_dt),
                (p.aspect[0], p.aspect[1], p.aspect[2]),
                round(p.angle_diff_min, 6),
                round(360.0 - p.angle_diff_min, 6)  # kept only if you still want this field
            ])
        return rows

    print("total rows count: ", len(periods))

    def print_periods(periods, limit=20):
        for i, p in enumerate(periods[:limit], 1):
            print(
                f"{i:02d} | {p.aspect[0]}-{p.aspect[1]}-{p.aspect[2]}  "
                f"start={format_dt(p.start_dt)}  exact={format_dt(p.exact_dt)}  end={format_dt(p.end_dt)}  "
                f"minΔ={p.angle_diff_min:.3f}°"
            )

    # for p in periods:
    #     print(f"{p.aspect}: {p.start_dt} to {p.end_dt}, exact on {p.exact_dt}, min angle diff {p.angle_diff:.2f}°")
    print_periods(periods, limit=10)

    # print("Planet Positions at Birth:", planet_position)
   