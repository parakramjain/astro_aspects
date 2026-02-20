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
from services.ai_prompt_service import get_system_prompt_report, get_user_prompt_report, get_user_prompt_daily, get_system_prompt_daily, get_user_prompt_weekly, get_system_prompt_weekly
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
        planet_exclusion_list = ["Moo"]
    elif req.timePeriod == "1D":
        end = start + dt.timedelta(days=1)
        step = 1
        # Very short window: exclude Moon to reduce noise
        planet_exclusion_list = ["Moo"]
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
        # transit_tz="UTC",
        transit_tz=req.timeZone,
        sample_step_hours=step,
        exclude_transit_short=planet_exclusion_list,
    )

    items: List[TimelineItem] = []
    # Mapping tables for building card IDs
    PLANET_CODE_MAP = {
        "Sun": "SUN", "Moo": "MOO", "Mer": "MER", "Ven": "VEN", "Mar": "MAR",
        "Jup": "JUP", "Sat": "SAT", "Ura": "URA", "Nep": "NEP", "Plu": "PLU",
    }
    ASPECT_CODE_MAP = {"Con": "CON", "Opp": "OPP", "Sqr": "SQR", "Tri": "TRI", "Sxt": "SXT"}

    for p in periods:
        t, a, n = p.aspect
        card_id = f"{PLANET_CODE_MAP.get(t, t.upper())}_{ASPECT_CODE_MAP.get(a, a.upper())}_{PLANET_CODE_MAP.get(n, n.upper())}__v1.0.0"

        desc_text: Optional[Dict[str, Any]] = None
        key_points: Optional[Dict[str, Any]] = None
        facets_points: Optional[Dict[str, Any]] = None
        keywords: Optional[Dict[str, Any]] = None

        aspect_nature = "Positive" if ASPECT_CODE_MAP.get(a, a.upper()) in {"CON", "TRI", "SXT"} else "Negative"

        try:
            sel = get_card_fields(card_id, fields="core_meaning, facets")
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

        except Exception as e:
            print(f"Error fetching card {card_id}: {e}")
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

def dailyWeeklyTimeline(payload: TimelineRequest, day_or_week: str = "daily", lang_code: str = 'en') -> DailyWeeklyData:
    """Build bilingual daily/weekly summary focused on description + facets."""

    import pytz
    from utils.timeline_report_pdf import create_timeline_pdf_report
    from utils.timeline_report_text import timeline_report_text
    from utils.timeline_report_plot import timeline_report_plot
    from utils.text_utils import strip_html

    # print("Generating PDF report...")
    timeline_output = compute_timeline(payload)   
    description = timeline_report_text(timeline_output, lang_code=lang_code)
    clean_description = strip_html(description)
    
    # print('Generating AI Summary...')
    AI_Summary = compute_daily_weekly_ai_summary(clean_description, payload=payload, day_or_week=day_or_week, lang_code=lang_code)

    return DailyWeeklyData(shortSummary=AI_Summary)

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

def compute_report_ai_summary(aspects_text: str, lang_code: str = "en") -> str:
    lang_code = "English" if lang_code.lower() == "en" else "Hindi"
    system_prompt = get_system_prompt_report()
    user_prompt = get_user_prompt_report(aspects_text, lang_code=lang_code)

    response_text = generate_astrology_AI_summary(system_prompt, user_prompt, model="gpt-4.1")
    return response_text

def compute_daily_weekly_ai_summary(aspects_text: str, payload: TimelineRequest, day_or_week: str = "daily",  lang_code: str = "en") -> str:
    day_or_week_norm = (day_or_week or "").strip().lower()

    if day_or_week_norm == "daily":
        system_prompt = get_system_prompt_daily(lang_code=lang_code)
        user_prompt = get_user_prompt_daily(aspects_text, payload=payload, lang_code=lang_code)
    elif day_or_week_norm == "weekly":
        system_prompt = get_system_prompt_weekly(lang_code=lang_code)
        user_prompt = get_user_prompt_weekly(aspects_text, payload=payload, lang_code=lang_code)
    else:
        raise ValueError(f"day_or_week must be 'daily' or 'weekly' (got: {day_or_week!r})")

    response_text = generate_astrology_AI_summary(system_prompt, user_prompt, model="gpt-4.1")
    return response_text

def generate_report_pdf(payload: TimelineRequest, lang_code= "en") -> str:
    import pytz
    from utils.timeline_report_pdf import create_timeline_pdf_report
    from utils.timeline_report_text import timeline_report_text
    from utils.timeline_report_plot import timeline_report_plot
    from utils.text_utils import strip_html

    # print("Generating PDF report...")
    timeline_output = compute_timeline(payload)   
    description = timeline_report_text(timeline_output, lang_code=lang_code)
    clean_description = strip_html(description)
    
    # print('Generating AI Summary...')
    AI_Summary = compute_report_ai_summary(clean_description, lang_code=lang_code)
    # AI_Summary = "This is a placeholder AI summary. Replace with actual AI-generated content."
    plot = timeline_report_plot(payload, timeline_output)
    pdf_path = create_timeline_pdf_report(payload, plot, description, ai_summary=AI_Summary, lang_code=lang_code)
    # print("Saved:", pdf_path)
    return pdf_path

if __name__ == "__main__":
    import pytz
    from utils.timeline_report_pdf import create_timeline_pdf_report
    from utils.timeline_report_text import timeline_report_text
    from utils.text_utils import strip_html

    print("Preparing payload...")
    payload = TimelineRequest(
            name="Meghna Jain",
            dateOfBirth="1980-02-01",
            timeOfBirth="11:30:00",
            placeOfBirth="Dewas, India",
            timeZone="Asia/Kolkata",
            latitude=22.97,
            longitude=76.05,
            timePeriod="1D",
            reportStartDate="2026-01-01",
    )

    # generate_report_pdf(payload, lang_code="en")
    output = dailyWeeklyTimeline(payload, day_or_week="daily", lang_code="hi")
    print("------"*10)
    print(output.shortSummary)
    print("------"*10)

    from utils.email_util import send_email
    name = 'Meghna Jain'
    email = 'jainmeghna@gmail.com'
    send_email(
                        to_email=email,
                        subject=f"{name} Your Daily Astro Aspects Report.",
                        body=f"{output.shortSummary}\n\nBest regards,\nAstro Consultant Team",
                        pdf_path='',
                    )
    print(f"Email sent to {email}")
    
    # timeline_output = compute_timeline(payload)   
    # description = timeline_report_text(timeline_output, lang_code="hi")
    # clean_description = strip_html(description)
    # print('Generating AI Summary...')
    # AI_Summary = compute_report_ai_summary(clean_description, lang_code="hi")
    # print(AI_Summary)
    # print("Process completed.")