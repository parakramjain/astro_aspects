from __future__ import annotations
import datetime as dt
from typing import List, Optional, Dict

# Removed unused import that could cause confusion; not needed for this module.

from aspect_card_utils.aspect_card_mgmt import get_card_fields
from schemas import (
    BirthPayload,
    DailyWeeklyData,
    LifeEvent,
    TimelineRequest,
    TimelineItem,
    TimelineData,
    DailyWeeklyOut
)
from astro_core.astro_core import calc_aspect_periods


def compute_life_events(
    payload: BirthPayload,
    start_date: Optional[dt.date] = None,
    horizon_days: int = 180,
    sample_step_hours: int = 6,
    limit: int = 50,
) -> List[LifeEvent]:
    """Compute upcoming life events using transit-to-natal aspect windows.

    Parameters:
    - payload: BirthPayload with DOB, TOB, TZ
    - start_date: anchor date (defaults to today)
    - horizon_days: days ahead to search (default 180)
    - sample_step_hours: sampling step for aspect search (default 6h)
    - limit: max number of aspect windows to include (default 50)

    Returns a list of LifeEvent models suitable for API response.
    """
    anchor = start_date or dt.date.today()
    end = anchor + dt.timedelta(days=horizon_days)
    # print("horizon_days: ", horizon_days)

    periods = calc_aspect_periods(
        birth_date=payload.dateOfBirth,
        birth_time=payload.timeOfBirth,
        birth_tz=payload.timeZone,
        start_date=anchor.isoformat(),
        end_date=end.isoformat(),
        transit_tz="UTC",
        sample_step_hours=sample_step_hours,
    )

    data: List[LifeEvent] = []
    # Mapping from SwissEphem short names (first 3 chars) to card planet codes used in KB.
    PLANET_CODE_MAP = {
        "Sun": "SUN", "Moo": "MOO", "Mer": "MER", "Ven": "VEN", "Mar": "MAR",
        "Jup": "JUP", "Sat": "SAT", "Ura": "URA", "Nep": "NEP", "Plu": "PLU",
    }
    # Aspect code mapping from internal short to card filenames. Sextile appears as 'SEX' in current KB.
    ASPECT_CODE_MAP = {"Con": "CON", "Opp": "OPP", "Sqr": "SQR", "Tri": "TRI", "Sxt": "SEX"}

    for p in periods[:limit]:
        t, a, n = p.aspect  # e.g. ('Jup','Con','Sun')
        event_type = "MAJOR" if t in {"Jup", "Sat", "Ura", "Nep", "Plu"} else "MINOR"
        startDate = p.start_dt.date().isoformat()
        endDate = p.end_dt.date().isoformat()
        exactDate = p.exact_dt.date().isoformat()
        span = f"{p.start_dt.date()} to {p.end_dt.date()}" 
        # Build card id using KB naming conventions (uppercase planet codes + aspect code).
        card_id = f"{PLANET_CODE_MAP.get(t, t.upper())}_{ASPECT_CODE_MAP.get(a, a.upper())}_{PLANET_CODE_MAP.get(n, n.upper())}__v1.0.0"
        description_text = ""
        try:
            # Fetch only the life_event_type field from the aspect card. The helper returns
            # a structure {"id": ..., "fields": {...}} so we must unwrap the "fields" key.
            raw_fields = get_card_fields(card_id, fields="life_event_type")
            life_event_value = raw_fields.get("fields", {}).get("life_event_type")
            # life_event_type in the card schema currently appears as a list (or may be missing).
            # Normalize to a human-readable string for the LifeEvent.description field (expects str).
            if isinstance(life_event_value, list):
                if life_event_value:
                    description_text = ", ".join(str(x) for x in life_event_value)
                else:
                    description_text = ""  # empty list -> empty description
            elif isinstance(life_event_value, (str, int, float)):
                description_text = str(life_event_value)
            elif life_event_value is None:
                description_text = ""  # missing -> empty
            else:
                description_text = str(life_event_value)
        except Exception:
            # Card might not exist yet; fallback description.
            description_text = ""  # leave blank; fill heuristic below.
        # Heuristic fallback if still blank.
        if not description_text:
            description_text = f"{PLANET_CODE_MAP.get(t, t)} {a} {PLANET_CODE_MAP.get(n, n)} transit window"
        data.append(
            LifeEvent(
                aspect=f"{t} {a} {n}",
                eventType=event_type,
                timePeriod=span,
                startDate=startDate,
                endDate=endDate,
                exactDate=exactDate,
                description=description_text,
            )
        )
    return data


def compute_timeline(req: TimelineRequest) -> TimelineData:
    """Build timeline items and summary for the given request.

    Encapsulates date range selection, sampling step, aspect window computation,
    and conversion to TimelineItem models.
    """
    print("Preparing timeline computation...")
    start = dt.date.fromisoformat(req.reportStartDate)
    planet_exclusion_list: List[str] = []
    if req.timePeriod == "1Y":
        end = start + dt.timedelta(days=365)
        step = 6
        planet_exclusion_list = ["Moo", "Mer", "Ven", "Sun", "Mar"]
    elif req.timePeriod == "6M":
        end = start + dt.timedelta(days=182)
        step = 6
        planet_exclusion_list = ["Moo", "Mer", "Ven", "Sun"]
    elif req.timePeriod == "1W":
        end = start + dt.timedelta(days=7)
        step = 1
        # Short window: exclude Moon to avoid excessive short-lived hits
        planet_exclusion_list = []
    elif req.timePeriod == "1D":
        end = start + dt.timedelta(days=1)
        step = 1
        # Very short window: exclude Moon to reduce noise
        planet_exclusion_list = []
    else:
        end = start + dt.timedelta(days=30)
        step = 3
        planet_exclusion_list = ["Moo"]

    periods = calc_aspect_periods(
        birth_date=req.dateOfBirth,
        birth_time=req.timeOfBirth,
        birth_tz=req.timeZone,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        transit_tz="UTC",
        sample_step_hours=step,
        exclude_transit_short=planet_exclusion_list,
    )

    items: List[TimelineItem] = []
    # Mapping tables for building card IDs
    PLANET_CODE_MAP = {
        "Sun": "SUN", "Moo": "MOO", "Mer": "MER", "Ven": "VEN", "Mar": "MAR",
        "Jup": "JUP", "Sat": "SAT", "Ura": "URA", "Nep": "NEP", "Plu": "PLU",
    }
    ASPECT_CODE_MAP = {"Con": "CON", "Opp": "OPP", "Sqr": "SQR", "Tri": "TRI", "Sxt": "SEX"}

    for p in periods:
        t, a, n = p.aspect
        # Build card_id and fetch description/actionables from the aspect card.
        card_id = f"{PLANET_CODE_MAP.get(t, t.upper())}_{ASPECT_CODE_MAP.get(a, a.upper())}_{PLANET_CODE_MAP.get(n, n.upper())}__v1.0.0"

        desc_text: Optional[str] = None
        key_points: Optional[Dict[str, List[str]]] = None
        facets_points: Optional[Dict[str, str]] = None

        try:
            sel = get_card_fields(card_id, fields="locales.hi.core,core_meaning,facets,actionables")
            fields = sel.get("fields", {})
            # Prefer localized core description
            loc = fields.get("locales", {})
            hi = loc.get("hi") if isinstance(loc, dict) else None
            if isinstance(hi, dict):
                desc_text = hi.get("core") or None
            if not desc_text:
                # Fallback to core_meaning
                cm = fields.get("core_meaning")
                if isinstance(cm, str):
                    desc_text = cm
            # Extract actionables -> include the full dict as-is (applying/exact/separating)
            acts = fields.get("actionables") if isinstance(fields, dict) else None
            if isinstance(acts, dict):
                # Use original shape so clients can decide how to display
                key_points = {k: [str(x) for x in v] for k, v in acts.items() if isinstance(v, list)}
            
            facets = fields.get("facets")
            print("Facets fetched for card_id ", card_id, ": ", facets)
            if isinstance(facets, dict):
                # Ensure facets_points is a dict before populating it
                if facets_points is None:
                    print("facets_points is None for card_id: ", card_id)
                    facets_points = {}
                for fk, fv in facets.items():
                    if isinstance(fv, str):
                        facets_points[fk] = str(fv)
        except Exception:
            # Missing card or unexpected structure; leave description/keyPoints as None
            pass

        items.append(
            TimelineItem(
                aspect=f"{t} {a} {n}",
                startDate=p.start_dt.isoformat(),
                exactDate=p.exact_dt.isoformat(),
                endDate=p.end_dt.isoformat(),
                description=desc_text,
                keyPoints=key_points,
                facets_points=facets_points
            )
        )
    summary = (
        f"Timeline for {req.name} starting {start.isoformat()} over {req.timePeriod}. "
        f"Generated from {len(items)} aspect windows."
    )
    return TimelineData(items=items, aiSummary=summary)

def dailyWeeklyTimeline(req: TimelineRequest) -> DailyWeeklyData:
    """Build daily/weekly summary for the given request.

    Encapsulates date range selection, sampling step, aspect window computation,
    and conversion to DailyWeeklyData models.
    """
    dailyWeeklyTimeline_data = compute_timeline(req)
    today = dt.date.today()
    # populate areas with the facets from timeline_data
    summary = f"{req.timePeriod} outlook generated for {req.name} on {today.isoformat()} (placeholder)."
    # areas is of type Dict
    areas: Dict[str, List] = {}
    print("Total items in dailyWeeklyTimeline_data.items:", len(dailyWeeklyTimeline_data.items))
    for item in dailyWeeklyTimeline_data.items:
        if isinstance(item.facets_points, dict):
            for key, value in item.facets_points.items():
                if key in areas:
                    existing = areas[key]
                    # If existing is a list, extend/append appropriately
                    if isinstance(existing, list):
                        if isinstance(value, list):
                            existing.extend(value)
                        else:
                            existing.append(value)
                    else:
                        # If existing is not a list, convert to list and merge
                        if isinstance(value, list):
                            areas[key] = [existing] + value
                        else:
                            areas[key] = [existing, value]
                else:
                    areas[key] = [value]

    return DailyWeeklyData(shortSummary=summary, areas=areas)

if __name__ == "__main__":
    # Simple test
    print("Preparing test payload...")
    payload = TimelineRequest(
            name="Amit",
            dateOfBirth="1951-08-04",
            timeOfBirth="16:00:00",
            placeOfBirth="Dewas, India",
            timeZone="Asia/Kolkata",
            latitude=22.72,
            longitude=75.80,
            timePeriod="1W",
            reportStartDate="2025-11-01",
    )

    # print("Computing life events...")
    # events = compute_life_events(payload)
    # print("Results:", len(events))
    # for ev in events:
    #     print(ev)

    timeline_output = compute_timeline(payload)
    print("Timeline Items:")
    for item in timeline_output.items:
        print(item.facets_points)
        print("-----"*20)
    print("Timeline Summary:")
    print(timeline_output.aiSummary)