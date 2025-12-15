from __future__ import annotations
import datetime as dt
from typing import List, Optional, Dict, Any
import ast

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
from services.ai_prompt_service import get_system_prompt_report, get_user_prompt_report, get_user_prompt_daily_weekly, get_system_prompt_daily_weekly
from services.ai_agent_services import generate_astrology_AI_summary

def compute_life_events(
    payload: BirthPayload,
    start_date: Optional[dt.date] = None,
    horizon_days: int = 1825,
    sample_step_hours: int = 24,
    limit: int = 5000,
) -> List[LifeEvent]:
    """Compute upcoming life events using transit-to-natal aspect windows.

    Parameters:
    - payload: BirthPayload with DOB, TOB, TZ
    - start_date: anchor date (defaults to today)
    - horizon_days: days ahead to search (default 180)
    - sample_step_hours: sampling step for aspect search (default 6h)
    - limit: max number of aspect windows to include (default 5000)

    Returns a list of LifeEvent models suitable for API response.
    """
    anchor = start_date or dt.date.today()
    end = anchor + dt.timedelta(days=horizon_days)

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
        aspect_nature = "Positive" if ASPECT_CODE_MAP.get(a, a.upper()) in {"CON", "TRI", "SXT"} else "Negative"
        if event_type == "MAJOR":
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
                    aspectNature=aspect_nature,
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
    print("===============================================================")
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

    print("Executing all aspects")
    for p in periods:
        t, a, n = p.aspect
        card_id = f"{PLANET_CODE_MAP.get(t, t.upper())}_{ASPECT_CODE_MAP.get(a, a.upper())}_{PLANET_CODE_MAP.get(n, n.upper())}__v1.0.0"

        desc_text: Optional[Dict[str, Any]] = None
        key_points: Optional[Dict[str, Any]] = None
        facets_points: Optional[Dict[str, Any]] = None
        keywords: Optional[Dict[str, Any]] = None

        aspect_nature = "Positive" if ASPECT_CODE_MAP.get(a, a.upper()) in {"CON", "TRI", "SXT"} else "Negative"

        try:
            sel = get_card_fields(card_id, fields="core_meaning,facets,actionables,keywords")
            fields = sel.get("fields", {}) if isinstance(sel, dict) else {}

            cm_value = fields.get("core_meaning") if isinstance(fields, dict) else None
            if isinstance(cm_value, dict):
                desc_text = cm_value
            else:
                desc_text = {"en": "", "hi": ""}

            acts = fields.get("actionables") if isinstance(fields, dict) else None
            if isinstance(acts, dict):
                key_points = acts
            else:
                key_points = {"applying": {"en": [], "hi": []}, "exact": {"en": [], "hi": []}, "separating": {"en": [], "hi": []}}

            facets = fields.get("facets") if isinstance(fields, dict) else None
            if isinstance(facets, dict):
                facets_points = facets or {}
            else:
                facets_points = { "career": { "en": " ", "hi": " "}, "relationships": {"en": " ", "hi": " "}, "money": {"en": " ","hi": " "},"health_adj": {"en": " ","hi": " "}}
            key_words = fields.get("keywords") if isinstance(fields, dict) else None
            if isinstance(key_words, dict):
                keywords=key_words

        except Exception:
            pass

        items.append(
            TimelineItem(
                aspect=f"{t} {a} {n}",
                aspectNature=aspect_nature,
                startDate=p.start_dt.isoformat(),
                exactDate=p.exact_dt.isoformat(),
                endDate=p.end_dt.isoformat(),
                description=desc_text,
                keyPoints=key_points,
                facetsPoints=facets_points,
                keywords=keywords
            )
        )
    summary = (
        f"Timeline for {req.name} starting {start.isoformat()} over {req.timePeriod}. "
        f"Generated from {len(items)} aspect windows."
    )
    return TimelineData(items=items, aiSummary=summary)

def dailyWeeklyTimeline(req: TimelineRequest) -> DailyWeeklyData:
    """Build bilingual daily/weekly summary focused on description + facets."""

    timeline = compute_timeline(req)
    today = dt.date.today()

    summary_map: Dict[str, List[str]] = {"en": [], "hi": []}
    areas: Dict[str, Dict[str, List[str]]] = {}

    def _extract_description_langs(value: Any) -> Dict[str, List[str]]:
        buckets: Dict[str, List[str]] = {"en": [], "hi": []}
        if isinstance(value, dict):
            for lang_code in ("en", "hi"):
                text_val = value.get(lang_code)
                if isinstance(text_val, str) and text_val.strip():
                    buckets[lang_code].append(text_val.strip())
        elif isinstance(value, str):
            parts = [segment.strip() for segment in value.split("\n") if segment.strip()]
            if parts:
                buckets["en"].append(parts[0])
            if len(parts) > 1:
                buckets["hi"].append(parts[1])
        return buckets

    def _parse_facets_value(value: Any) -> Dict[str, List[str]]:
        localized: Dict[str, List[str]] = {"en": [], "hi": []}
        if isinstance(value, dict):
            for lang_code in ("en", "hi"):
                lang_val = value.get(lang_code)
                if isinstance(lang_val, str) and lang_val.strip():
                    localized[lang_code].append(lang_val.strip())
                elif isinstance(lang_val, list):
                    localized[lang_code].extend(str(item).strip() for item in lang_val if str(item).strip())
        elif isinstance(value, str):
            for line in value.split("\n"):
                cleaned = line.strip()
                if not cleaned or ":" not in cleaned:
                    continue
                prefix, text = cleaned.split(":", 1)
                lang_key = prefix.strip().lower()
                if lang_key in localized and text.strip():
                    localized[lang_key].append(text.strip())
        return localized

    def _ensure_area_bucket(area_key: str) -> Dict[str, List[str]]:
        bucket = areas.setdefault(area_key, {"en": [], "hi": []})
        for lang_code in ("en", "hi"):
            bucket.setdefault(lang_code, [])
        return bucket

    for item in timeline.items:
        desc_langs = _extract_description_langs(item.description)
        for lang_code, entries in desc_langs.items():
            for entry in entries:
                if entry and entry not in summary_map[lang_code]:
                    summary_map[lang_code].append(entry)

        facets = item.facetsPoints
        if not isinstance(facets, dict):
            continue
        for area_key, raw_value in facets.items():
            lang_entries = _parse_facets_value(raw_value)
            if not lang_entries["en"] and not lang_entries["hi"]:
                continue
            bucket = _ensure_area_bucket(area_key)
            for lang_code, entries in lang_entries.items():
                for entry in entries:
                    if entry and entry not in bucket[lang_code]:
                        bucket[lang_code].append(entry)

    fallback = f"{req.timePeriod} outlook generated for {req.name} on {today.isoformat()}."
    summary_out: Dict[str, Optional[str]] = {
        "en": "\n\n".join(summary_map["en"]) if summary_map["en"] else fallback,
        "hi": "\n\n".join(summary_map["hi"]) if summary_map["hi"] else None,
    }
    if summary_out["hi"] is None:
        summary_out["hi"] = summary_out["en"]

    return DailyWeeklyData(shortSummary=summary_out, areas=areas)

def upcoming_event(
    events: List[LifeEvent],
    from_date: Optional[dt.date] = None,
    to_date: Optional[dt.date] = None,
) -> List[Dict[str, Any]]:
    """Expand LifeEvent windows into per-day calendar entries.

    Input event format (per LifeEvent):
      - timePeriod: "YYYY-MM-DD to YYYY-MM-DD" (inclusive)
      - startDate/endDate: ISO dates (preferred when present)
      - description: may be plain string or a stringified dict like
        "{'en': [...], 'hi': [...]}".

    Returns:
      A list sorted by date:
        [{"date": "YYYY-MM-DD", "events": [{"aspect": str, "aspectNature": str, "description": Any}, ...]}, ...]

    Notes:
      - Each aspect is included for every day in its window (inclusive).
      - If from_date/to_date are provided, results are clipped to that range.
    """

    if from_date is not None:
        anchor = from_date
    else:
        today = dt.date.today()
        anchor = today.replace(day=1)

    def _parse_date(val: Any) -> Optional[dt.date]:
        if not val:
            return None
        try:
            return dt.date.fromisoformat(str(val)[:10])
        except Exception:
            return None

    def _event_range(ev: LifeEvent) -> Optional[tuple[dt.date, dt.date]]:
        start = _parse_date(getattr(ev, "startDate", None))
        end = _parse_date(getattr(ev, "endDate", None))
        if start and end:
            return start, end
        # fallback to timePeriod parsing: "YYYY-MM-DD to YYYY-MM-DD"
        tp = getattr(ev, "timePeriod", "")
        if isinstance(tp, str) and "to" in tp:
            left, right = tp.split("to", 1)
            start2 = _parse_date(left.strip())
            end2 = _parse_date(right.strip())
            if start2 and end2:
                return start2, end2
        return None

    def _normalize_description(desc: Any) -> Any:
        if not isinstance(desc, str):
            return desc
        s = desc.strip()
        if not s:
            return desc
        # Safe parse for strings like "{'en': [...], 'hi': [...]}"
        if s.startswith("{") and s.endswith("}") and ("'en'" in s or '"en"' in s):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return desc
        return desc

    daily: Dict[dt.date, List[Dict[str, Any]]] = {}
    for ev in events:
        rng = _event_range(ev)
        if not rng:
            continue
        start, end = rng
        if end < anchor:
            continue
        start_clip = max(start, anchor)
        end_clip = end
        if to_date is not None:
            if start_clip > to_date:
                continue
            end_clip = min(end_clip, to_date)

        desc_out = _normalize_description(getattr(ev, "description", ""))
        d = start_clip
        while d <= end_clip:
            daily.setdefault(d, []).append(
                {
                    "aspect": ev.aspect,
                    "aspectNature": ev.aspectNature,
                    "description": desc_out,
                }
            )
            d += dt.timedelta(days=1)

    out: List[Dict[str, Any]] = []
    for day in sorted(daily.keys()):
        out.append({"date": day.isoformat(), "events": daily[day]})
    return out

def compute_report_ai_summary(aspects_text: str) -> str:
    system_prompt = get_system_prompt_report()
    user_prompt = get_user_prompt_report(aspects_text)

    response_text = generate_astrology_AI_summary(system_prompt, user_prompt, model="gpt-4.1")
    return response_text

def compute_daily_weekly_ai_summary(aspects_text: str) -> str:
    print("Generating daily/weekly AI summary...")
    system_prompt = get_system_prompt_daily_weekly()
    user_prompt = get_user_prompt_daily_weekly(aspects_text)

    response_text = generate_astrology_AI_summary(system_prompt, user_prompt, model="gpt-4.1")
    return response_text


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
            timePeriod="1D",
            reportStartDate="2025-11-01",
    )

    # print("Computing life events...")
    # events = compute_life_events(payload)
    # print("Results:", len(events))
    # for ev in events:
    #     print(ev)

    # timeline_output = compute_timeline(payload)
    # print("Timeline Items:")
    # for item in timeline_output.items:
    #     print(item.facets_points)
    #     print("-----"*20)
    # print("Timeline Summary:")
    # print(timeline_output.aiSummary)

    output = dailyWeeklyTimeline(payload)
    print("Daily/Weekly Output Summary:")
    print(output)