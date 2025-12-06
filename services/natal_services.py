import datetime as dt
from typing import Dict, Tuple, List, Optional
from zoneinfo import ZoneInfo
import swisseph as swe

# Centralized ayanamsha + flags from astro_core

from astro_core.astro_core import (
    set_ayanamsha,
    get_flags,
    PLANET_FULL_NAMES,
    ASPECTS,
    ASPECT_ORB_DEG,
    NATAL_ASPECT_ORB_DEG,
    AYANAMSHA_MAP,
    SIDEREAL_ENABLED,
    current_ayanamsha_info,
)

from aspect_card_utils.aspect_card_mgmt import get_card_fields

from schemas import (
    BirthPayload,
    PlanetEntry,
    NatalChartOut, NatalChartData,
    DignitiesOut, DignitiesData, DignityRow,
    NatalAspectsOut, NatalAspectItem,
    NatalCharacteristicsOut, NatalCharacteristicsData, KpiItem,
    LifeEventsOut, LifeEvent,
    TimelineRequest, TimelineOut, TimelineData, TimelineItem,
    DailyWeeklyRequest, DailyWeeklyOut, DailyWeeklyData, DailyArea,
    UpcomingEventsOut, UpcomingEventRow, UpcomingEventWindow,
    CompatibilityPairIn, CompatibilityOut, CompatibilityData, KpiScoreRow,
    GroupCompatibilityIn, GroupCompatibilityOut, GroupCompatibilityData, PairwiseRow,
    SoulmateOut, SoulmateData,
)
from services.ai_prompt_service import get_system_prompt_natal, get_user_prompt_natal

PLANET_IDS = list(range(swe.SUN, swe.PLUTO + 1))

def _to_utc(dt_local: dt.datetime, tz: ZoneInfo) -> dt.datetime:
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=tz)
    return dt_local.astimezone(dt.UTC)

def _julday_utc(dtu: dt.datetime) -> float:
    dtu = dtu.astimezone(dt.UTC)
    frac = dtu.hour + dtu.minute / 60.0 + dtu.second / 3600.0 + dtu.microsecond / 3_600_000_000.0
    return swe.julday(dtu.year, dtu.month, dtu.day, frac)

def _planet_longitudes_utc(dtu: dt.datetime, flags: int) -> Dict[int, float]:
    jd_ut = _julday_utc(dtu)
    out: Dict[int, float] = {}
    for pid in PLANET_IDS:
        pos, _ = swe.calc_ut(jd_ut, pid, flags)
        out[pid] = pos[0]  # ecliptic longitude
    return out

def _houses_compat(jd_ut, lat_deg, lon_deg, hsys: str, flags: int):
    """
    Version- and build-compatible call into Swiss Ephemeris house functions.
    Ensures hsys is a single BYTE (e.g. b'P'), and tries (flags) form first,
    then falls back to the no-flags form, then to houses().
    """
    if not isinstance(hsys, (bytes, bytearray)):
        if not isinstance(hsys, str) or len(hsys) == 0:
            raise ValueError("house system code must be a 1-char string like 'P','E','O','K', etc.")
        hsys_b = hsys[0].encode("ascii", errors="strict")
    else:
        hsys_b = hsys[:1]

    # Try houses_ex with flags
    try:
        return swe.houses_ex(jd_ut, flags, lat_deg, lon_deg, hsys_b)
    except TypeError:
        # Fall back: houses_ex without flags
        try:
            return swe.houses_ex(jd_ut, lat_deg, lon_deg, hsys_b)
        except TypeError:
            # Final fallback: houses()
            return swe.houses(jd_ut, lat_deg, lon_deg, hsys_b)

def _asc_mc_and_cusps_utc(
    dtu: dt.datetime,
    lat_deg: float,
    lon_deg: float,
    house_sys: str = "P",   # 'P' Placidus, 'E' Equal, 'O' Porphyry, etc.
    flags: Optional[int] = None,
) -> Tuple[List[float], List[float]]:
    """
    Returns (cusps[1..12], ascmc[0..9]).
    ascmc[0]=Asc, ascmc[1]=MC per Swiss Ephemeris.
    """
    jd_ut = _julday_utc(dtu)
    if flags is None:
        flags = get_flags()
    # SwissEphem expects east longitudes as positive; pass your lon accordingly.
    # print(f"Calculating houses for: {jd_ut}, {flags}, {lat_deg}, {lon_deg}, {house_sys}")
    cusps, ascmc = _houses_compat(jd_ut, lat_deg, lon_deg, house_sys, flags)
    return cusps, ascmc

def _sign_index(longitude_deg: float) -> int:
    """0..11 for Aries..Pisces on sidereal circle."""
    return int((longitude_deg % 360.0) // 30.0)

def _house_whole_sign(planet_lon: float, asc_lon: float) -> int:
    asc_sign = _sign_index(asc_lon)
    p_sign = _sign_index(planet_lon)
    return ((p_sign - asc_sign) % 12) + 1  # 1..12

def _normalize_deg(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0

def _wrap_cusp_segment(a: float, b: float, x: float) -> bool:
    """
    Returns True if angle x lies within arc a->b going forward (wrapping 360).
    All in [0,360).
    """
    a = _normalize_deg(a); b = _normalize_deg(b); x = _normalize_deg(x)
    if a <= b:
        return a <= x < b
    else:
        return (x >= a) or (x < b)

def _as_12_cusps(cusps_obj) -> list[float]:
    """
    Normalize Swiss Ephemeris cusp outputs to a 12-length, 0-based list.
    Accepts 12-length (0..11) or 13-length (0..12 with cusps[0] unused).
    """
    seq = list(cusps_obj)
    if len(seq) == 13:
        # Swiss style: cusps[1..12] valid, [0] unused
        seq12 = seq[1:13]
    elif len(seq) == 12:
        # Already 12 values, 0..11
        seq12 = seq
    else:
        raise ValueError(f"Unexpected number of cusps: {len(seq)} (expected 12 or 13)")
    return [_normalize_deg(x) for x in seq12]

def _house_by_cusps(planet_lon: float, cusps: List[float]) -> int:
    """
    House by quadrant system cusps: find segment between cusp i and i+1 (wrapping).
    cusps should be 1-based (Swiss returns 13-length, index 1..12 meaningful).
    """
    c = _as_12_cusps(cusps)  # now 12 items, 0..11
    for i in range(12):
        a = c[i]
        b = c[(i + 1) % 12]
        if _wrap_cusp_segment(a, b, planet_lon):
            return i + 1  # 1..12
    return 12  # fallback

# --- Sign helpers ------------------------------------------------------------
SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

def _norm360(x: float) -> float:
    x %= 360.0
    return x if x >= 0 else x + 360.0

def lon_to_sign_deg_min(lon_deg: float) -> tuple[str, int, int]:
    """
    Convert ecliptic longitude (deg) to (sign_name, deg_in_sign, minutes).
    Rounds to nearest arcminute and keeps 0–29° in the sign.
    """
    L = _norm360(lon_deg)
    sign_index = int(L // 30)
    sign_name = SIGN_NAMES[sign_index]
    within = L - 30 * sign_index             # 0..30
    total_minutes = int(round(within * 60))  # round to minute

    # Handle 60' rollover -> bump degree; 30° rollover -> next sign
    deg_in_sign, minutes = divmod(total_minutes, 60)
    if deg_in_sign == 30:
        sign_index = (sign_index + 1) % 12
        sign_name = SIGN_NAMES[sign_index]
        deg_in_sign = 0

    return sign_name, deg_in_sign, minutes

def format_lon_as_sign(lon_deg: float) -> str:
    sign, d, m = lon_to_sign_deg_min(lon_deg)
    return f"{d:02d}° {m:02d}' {sign}"

def planet_positions_and_houses(
    birth_date: str | dt.date | dt.datetime,
    birth_time: Optional[str],
    birth_tz: str,
    lat_deg: float,
    lon_deg: float,
    *,
    ayanamsha_mode: str = "sidereal",
    ayanamsha_name: str = "Lahiri",
    ayanamsha_custom_offset_deg: float | None = None,
    house_system: str = "WHOLE",  # "WHOLE" for Whole Sign; or Swiss code like "P", "E", "O"
) -> Dict[str, dict]:
    """
    Returns:
      {
        "Sun": {"lon": 108.06, "house": 11},
        "Moo": {"lon": 124.86, "house": 12},
        ...
        "_asc": {"lon": 123.45, "house": 1},
        "_mc":  {"lon": 210.12}
      }
    """
    # Configure ayanamsha for this run
    set_ayanamsha(ayanamsha_mode, ayanamsha_name, ayanamsha_custom_offset_deg)
    flags = get_flags()

    # Debug: Ayana info
    # print("[ayanamsha]", current_ayanamsha_info())
    # Build local datetime from inputs
    if isinstance(birth_date, str):
        d = dt.date.fromisoformat(birth_date)
    elif isinstance(birth_date, dt.datetime):
        d = birth_date.date()
    elif isinstance(birth_date, dt.date):
        d = birth_date
    else:
        raise TypeError("birth_date must be str/date/datetime")

    if birth_time:
        parts = [int(x) for x in birth_time.split(":")]
        if len(parts) == 2:
            hh, mm = parts; ss = 0
        else:
            hh, mm, ss = parts
    else:
        hh = mm = ss = 0

    local_dt = dt.datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=ZoneInfo(birth_tz))
    utc_dt = _to_utc(local_dt, ZoneInfo(birth_tz))

    # Planet longitudes (respect current ayanamsha setting)
    plon = _planet_longitudes_utc(utc_dt, flags=flags)

    # Asc/MC + cusps
    if house_system == "WHOLE":
        # compute Asc via a standard system (Equal is fine) then assign by sign distance
        cusps, ascmc = _asc_mc_and_cusps_utc(utc_dt, lat_deg, lon_deg, house_sys="E", flags=flags)
        asc = ascmc[0]
    else:
        cusps, ascmc = _asc_mc_and_cusps_utc(utc_dt, lat_deg, lon_deg, house_sys=house_system, flags=flags)
        asc = ascmc[0]

    asc = ascmc[0]   # Ascendant longitude
    mc  = ascmc[1]   # Midheaven longitude

    out: Dict[str, dict] = {}
    for pid, lon in plon.items():
        short = swe.get_planet_name(pid)[:3]
        if house_system == "WHOLE":
            h = _house_whole_sign(lon, asc)
        else:
            h = _house_by_cusps(lon, cusps)
        house_name = SIGN_NAMES[(h - 1) % 12]
        out[short] = {"lon": round(lon, 2), "house": h, "house_name": house_name}

    # add Asc and MC info
    out["_asc"] = {"lon": round(asc, 2), "house": 1}  # Asc is always House 1 by definition
    out["_mc"]  = {"lon": round(mc, 2)}

    # For quadrant systems, you may also want to include the 12 cusps:
    # 1..12 cusps (Swiss Ephem returns index 1..12 meaningful when length=13)
    try:
        out["_cusps"] = {str(i): round(cusps[i], 2) for i in range(1, 13)}
    except Exception:
        # In rare builds cusps may be a 12-length list (0..11). Normalize via helper to ensure 12 values
        c12 = _as_12_cusps(cusps)
        out["_cusps"] = {str(i+1): round(c12[i], 2) for i in range(12)}

    # Optionally include ayanamsha info for debugging
    out["_ayanamsha"] = current_ayanamsha_info()

    return out

def calculate_natal_chart_data(payload: BirthPayload) -> NatalChartData:
    pos = planet_positions_and_houses(
        birth_date=payload.dateOfBirth,
        birth_time=payload.timeOfBirth,
        birth_tz=payload.timeZone,
        lat_deg=payload.latitude,
        lon_deg=payload.longitude,
        house_system="WHOLE",
    )
    planets: List[PlanetEntry] = []
    # Include only actual planets Sun..Pluto keys by 3-letter code present in result
    for short, data in pos.items():
        if short.startswith("_") and (short != "_asc"):
            continue
        sign_name, deg_in_sign, minutes = lon_to_sign_deg_min(data["lon"])  # noqa: F405
        house_num = int(data.get("house", 1))
        house_name = [
            "First House","Second House","Third House","Fourth House","Fifth House","Sixth House",
            "Seventh House","Eighth House","Ninth House","Tenth House","Eleventh House","Twelfth House",
        ][(house_num - 1) % 12]
        
        planets.append(
            PlanetEntry(
            planetName=PLANET_FULL_NAMES.get(short, short),  # use full name when available
            planetSign=sign_name,
            planetDegree=round(deg_in_sign + minutes / 60.0, 2),
            houseNumber=house_num,
            houseName=house_name,
            houseSign=SIGN_NAMES[(house_num - 1) % 12],  # approximate for Whole Sign
            )
        )
    return NatalChartData(planets=planets)

def compute_natal_natal_aspects(payload: BirthPayload) -> List[NatalAspectItem]:
    # Pairwise planet aspects using aspect orbs
    pos = planet_positions_and_houses(
        birth_date=payload.dateOfBirth,
        birth_time=payload.timeOfBirth,
        birth_tz=payload.timeZone,
        lat_deg=payload.latitude,
        lon_deg=payload.longitude,
        house_system="WHOLE",
    )
    # Convert to longitudes dict
    longitudes = {k: v["lon"] for k, v in pos.items() if not k.startswith("_")}

    items: List[NatalAspectItem] = []
    keys = [k for k in longitudes.keys() if not k.startswith("_")]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            la, lb = longitudes[a], longitudes[b]
            sep = abs((la - lb) % 360.0)
            if sep > 180:
                sep = 360 - sep
            for angle, code in ASPECTS.items():
                orb = NATAL_ASPECT_ORB_DEG.get(angle, 3.0)
                dist = abs(sep - angle)
                if dist <= orb:
                    strength = max(0.0, 1.0 - dist / max(orb, 1e-6))
                    label = f"{a} {code} {b}"
                    # print(f"{a}_{code}_{b}__v1.0.0")
                    # Get the description and facets from aspect cards
                    card_fields = get_card_fields(f"{a}_{code}_{b}__v1.0.0", fields="core_meaning,facets").get("fields", {})
                    items.append(NatalAspectItem(aspect=label, angle=round(sep, 3), dist=round(dist, 3), strength=round(strength, 3), characteristics=card_fields))
    # Sort by strength desc
    items.sort(key=lambda x: x.strength, reverse=True)
    return items

def compute_natal_ai_summary(aspects_text: List[NatalAspectItem]) -> str:
    system_prompt = get_system_prompt_natal()
    user_prompt = get_user_prompt_natal(aspects_text)

    from services.ai_agent_services import generate_astrology_AI_summary

    response_text = generate_astrology_AI_summary(system_prompt, user_prompt, model="gpt-4.1")
    return response_text

if __name__ == "__main__":
    # Demonstration: Sidereal Lahiri (default), Tropical, and USER custom offset
    name = "Amit"
    dateOfBirth = "1991-07-14"
    timeOfBirth = "22:35:00"
    placeOfBirth = "Mumbai, IN"
    timeZone = "Asia/Kolkata"
    latitude = 19.076
    longitude = 72.8777

    print("-- Sidereal (Lahiri, default) --")
    res_sid = planet_positions_and_houses(
        birth_date=dateOfBirth,
        birth_time=timeOfBirth,
        birth_tz=timeZone,
        lat_deg=latitude,
        lon_deg=longitude,
        house_system="WHOLE",
    )
    # Print all planet positions
    for planet_short in res_sid.keys():
        if planet_short.startswith("_"):
            continue
        print(f"{planet_short}: {format_lon_as_sign(res_sid[planet_short]['lon'])}")
        
    # print("-- Tropical --")
    # res_trop = planet_positions_and_houses(
    #     birth_date=dateOfBirth,
    #     birth_time=timeOfBirth,
    #     birth_tz=timeZone,
    #     lat_deg=latitude,
    #     lon_deg=longitude,
    #     house_system="WHOLE",
    #     ayanamsha_mode="tropical",
    #     ayanamsha_name="Tropical",
    # )
    # print("Sun:", format_lon_as_sign(res_trop["Sun"]["lon"]))

    # print("-- Sidereal (USER offset 23.85°) --")
    # res_user = planet_positions_and_houses(
    #     birth_date=dateOfBirth,
    #     birth_time=timeOfBirth,
    #     birth_tz=timeZone,
    #     lat_deg=latitude,
    #     lon_deg=longitude,
    #     house_system="WHOLE",
    #     ayanamsha_mode="sidereal",
    #     ayanamsha_name="USER",
    #     ayanamsha_custom_offset_deg=23.85,
    # )
    # print("Sun:", format_lon_as_sign(res_user["Sun"]["lon"]))

    # # Simple self-check: ensure tropical differs from sidereal
    # sun_sid = res_sid["Sun"]["lon"]
    # sun_tro = res_trop["Sun"]["lon"]
    # delta = abs((sun_tro - sun_sid) % 360)
    # delta = 360 - delta if delta > 180 else delta
    # print("Delta(Sid vs Trop) ≈", round(delta, 2), "deg")