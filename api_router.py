from __future__ import annotations
import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Optional, List, Dict, Annotated, Any
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Body

from schemas import (
    LifeEventPayload,
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
    AshtakootaOut, AshtakootaData,
)

from services.natal_services import planet_positions_and_houses, compute_natal_natal_aspects, calculate_natal_chart_data, lon_to_sign_deg_min, SIGN_NAMES,compute_natal_ai_summary
from astro_core.astro_core import calc_aspect_periods, ASPECTS, ASPECT_ORB_DEG, _delta_circ  # type: ignore
from services.report_services import compute_life_events, compute_timeline, dailyWeeklyTimeline, compute_report_ai_summary, compute_daily_weekly_ai_summary
from services.synastry_services import calculate_synastry  # newly added synastry pipeline
from services.synastry_vedic_services import compute_ashtakoota_score, explain_ashtakoota
from services.synastry_group_services import (
    analyze_group as sg_analyze_group,
    PersonInput as SGPersonInput,
    kpi_catalog as sg_kpi_catalog,
    analyze_group_api_payload as sg_build_group_api_payload,
    is_supported_type as sg_is_supported_type,
    COMPATIBILITY_TYPES as SG_COMPAT_TYPES,
)


def _require_api_headers(
    x_correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-ID")] = None,
    x_transaction_id: Annotated[Optional[str], Header(alias="X-Transaction-ID")] = None,
    x_session_id: Annotated[Optional[str], Header(alias="X-Session-ID")] = None,
    x_app_id: Annotated[Optional[str], Header(alias="X-App-ID")] = None,
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> None:
    if not authorization or not str(authorization).strip():
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    missing = []
    if not x_correlation_id:
        missing.append("X-Correlation-ID")
    if not x_transaction_id:
        missing.append("X-Transaction-ID")
    if not x_session_id:
        missing.append("X-Session-ID")
    if not x_app_id:
        missing.append("X-App-ID")

    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required headers: {', '.join(missing)}")


router = APIRouter(prefix="/api", dependencies=[Depends(_require_api_headers)])


# --------------------- Helpers ---------------------
# Meta headers removed as per request


def _ensure_dict_from_ai_summary(summary: Any) -> Dict[str, Any]:
    """Coerce the AI summary output into a dictionary for Pydantic."""
    if isinstance(summary, dict):
        return summary
    if isinstance(summary, str):
        text = summary.strip()
        if not text:
            return {"text": ""}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"text": parsed}
        except json.JSONDecodeError:
            return {"text": text}
    return {"text": str(summary)}



# --------------- Natal -----------------
@router.post("/natal/build-chart", response_model=NatalChartOut, tags=["Natal"], summary="Build Natal Chart (positions, signs, houses)")
def build_natal_chart(
    payload: BirthPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                },
            }
        },
    ),
) -> NatalChartOut:
    out_item = calculate_natal_chart_data(payload)
    return NatalChartOut(data=out_item)


@router.post("/natal/dignities-table", response_model=DignitiesOut, tags=["Natal"], summary="Compute Dignities Table")
def dignities_table(
    payload: BirthPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                },
            }
        },
    ),
) -> DignitiesOut:
    # Placeholder implementation — returns dummy dignity flags and computed scores
    planets = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
    table: List[DignityRow] = []
    for p in planets:
        table.append(
            DignityRow(
                planet=p,
                rulership=False,
                exaltation=False,
                detriment=False,
                fall=False,
                essentialScore=0.0,
                notes="N/A",
            )
        )
    return DignitiesOut(data=DignitiesData(table=table))

@router.post("/natal/aspects", response_model=NatalAspectsOut, tags=["Natal"], summary="Compute Natal Aspects & Characteristics")
def natal_aspects(
    payload: BirthPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                },
            }
        },
    ),
) -> NatalAspectsOut:
    items = compute_natal_natal_aspects(payload)
    return NatalAspectsOut(data=items)

# Need to update below API to use aspect cards for characteristics. Currently aspects is providing both the aspect list and characteristics.
@router.post("/natal/characteristics", response_model=NatalCharacteristicsOut, tags=["Natal"], summary="Compute Natal Characteristics & KPI summary")
def natal_characteristics(
    payload: BirthPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                },
            }
        },
    ),
) -> NatalCharacteristicsOut:
    items = compute_natal_natal_aspects(payload)
    ai_summary = compute_natal_ai_summary(items)
    summary_dict = _ensure_dict_from_ai_summary(ai_summary)
    return NatalCharacteristicsOut(data=NatalCharacteristicsData(description=summary_dict))


# --------------- Reports -----------------
@router.post("/reports/life-events", response_model=LifeEventsOut, tags=["Reports"], summary="Major & minor life events (summary windows)")
def life_events(
    payload: LifeEventPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1991-07-14",
                    "timeOfBirth": "22:35:00",
                    "placeOfBirth": "Mumbai, IN",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 19.0760,
                    "longitude": 72.8777,
                    "start_date": "2025-11-01",
                    "horizon_days": 90,
                },
            }
        },
    ),
) -> LifeEventsOut:
    # start_date and horizon_days are query params (not added to BirthPayload)
    print(f"Computing life events report... start_date={payload.start_date} horizon_days={payload.horizon_days}")
    # Convert start_date (string) to a datetime.date if provided
    start_date_date: Optional[dt.date] = None
    if payload.start_date:
        try:
            start_date_date = dt.date.fromisoformat(payload.start_date)
        except ValueError:
            # invalid date format in query param
            raise HTTPException(status_code=400, detail="start_date must be in YYYY-MM-DD format")

    # Delegate main processing to report services for testability/reuse
    # Try to pass the extra params to compute_life_events if it supports them, otherwise fall back.
    try:
        data: List[LifeEvent] = compute_life_events(payload, start_date=start_date_date, horizon_days=payload.horizon_days)
    except TypeError:
        data: List[LifeEvent] = compute_life_events(payload)
    return LifeEventsOut(data=data)


@router.post("/reports/timeline", response_model=TimelineOut, tags=["Reports"], summary="Report timeline with aspect windows and AI summary")
def report_timeline(
    req: TimelineRequest = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                    "timePeriod": "6M",
                    "reportStartDate": "2025-11-01",
                    "cursor": None,
                },
            }
        },
    ),
) -> TimelineOut:
    timeline_data = compute_timeline(req)

    try:
        items_payload = [
            item.model_dump() if hasattr(item, "model_dump") else item.dict()  # type: ignore[union-attr]
            for item in timeline_data.items
        ]
        aspects_text = json.dumps(items_payload, ensure_ascii=False)
        timeline_data.aiSummary = compute_report_ai_summary(aspects_text)
    except Exception as e:
        # If AI summary generation fails, continue returning structural data
        print(f"[reports/timeline] AI summary generation failed: {e}")

    return TimelineOut(data=timeline_data)


@router.post("/reports/daily-weekly", response_model=DailyWeeklyOut, tags=["Reports"], summary="Daily/Weekly prediction update")
def daily_weekly(
    req: TimelineRequest = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1951-08-04",
                    "timeOfBirth": "16:00:00",
                    "placeOfBirth": "Dewas, India",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 22.72,
                    "longitude": 75.80,
                    "timePeriod": "1D",
                    "reportStartDate": "2025-11-01",
                    "cursor": None,
                },
            }
        },
    ),
) -> DailyWeeklyOut:
    dailyWeeklyTimeline_data = dailyWeeklyTimeline(req)

    try:
        items_payload = [
            item.model_dump() if hasattr(item, "model_dump") else item.dict()  # type: ignore[union-attr]
            for item in dailyWeeklyTimeline_data.data
        ]
        aspects_text = json.dumps(items_payload, ensure_ascii=False)
        dailyWeeklyTimeline_data = compute_daily_weekly_ai_summary(aspects_text)
    except Exception as e:
        # If AI summary generation fails, continue returning structural data
        print(f"[reports/timeline] AI summary generation failed: {e}")
        
    return DailyWeeklyOut(data=dailyWeeklyTimeline_data)


@router.post("/reports/upcoming-events", response_model=LifeEventsOut, tags=["Reports"], summary="Upcoming major/minor events with categories")
def upcoming_events(
    payload: LifeEventPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1991-07-14",
                    "timeOfBirth": "22:35:00",
                    "placeOfBirth": "Mumbai, IN",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 19.0760,
                    "longitude": 72.8777,
                    "start_date": "2025-11-01", # 1st of current month
                    "horizon_days": 365,
                },
            }
        },
    ),
) -> LifeEventsOut:
    print(f"Computing upcoming events report... start_date={payload.start_date} horizon_days={payload.horizon_days}")
    # Convert start_date (string) to a datetime.date if provided
    start_date_date: Optional[dt.date] = None
    if payload.start_date:
        try:
            start_date_date = dt.date.fromisoformat(payload.start_date)
        except ValueError:
            # invalid date format in query param
            raise HTTPException(status_code=400, detail="start_date must be in YYYY-MM-DD format")

    # Delegate main processing to report services for testability/reuse
    # Try to pass the extra params to compute_life_events if it supports them, otherwise fall back.
    try:
        data: List[LifeEvent] = compute_life_events(payload, start_date=start_date_date, horizon_days=payload.horizon_days)
    except TypeError:
        data: List[LifeEvent] = compute_life_events(payload)
    return LifeEventsOut(data=data)


# --------------- Compatibility -----------------
@router.post("/compat/synastry", response_model=CompatibilityOut, tags=["Compatibility"], summary="Compatibility finder (pairwise)")
def compat_pair(
    req: CompatibilityPairIn = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "person1": {
                        "name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN",
                        "timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777
                    },
                    "person2": {
                        "name": "Riya","dateOfBirth": "1993-02-20","timeOfBirth": "06:10:00","placeOfBirth": "Delhi, IN",
                        "timeZone": "Asia/Kolkata","latitude": 28.6139,"longitude": 77.2090
                    },
                    "type": "General"
                },
            }
        },
    ),
) -> CompatibilityOut:
    # Execute real synastry calculation using new services.synastry module
    # Extract raw dicts from Pydantic models (v2 uses model_dump)
    p1 = req.person1.model_dump() if hasattr(req.person1, "model_dump") else req.person1.dict()
    p2 = req.person2.model_dump() if hasattr(req.person2, "model_dump") else req.person2.dict()

    syn = calculate_synastry(p1, p2)

    # Build KPI rows (normalize 0-10 synastry scores to 0-1 for API consistency)
    kpi_map = syn.get("kpi_scores", {})
    kpi_rows: List[KpiScoreRow] = []
    for key, val in kpi_map.items():
        label = key.replace("_", " ").title()
        # Each val is 0..10; convert to 0..1 scale and round
        score_norm = round(float(val) / 10.0, 2)
        # Provide brief description heuristics
        desc = None
        if key == "emotional":
            desc = "Moon & Venus/Moon aspects emotional rapport"
        elif key == "communication":
            desc = "Mercury links support mental exchange"
        elif key == "chemistry":
            desc = "Venus-Mars/Sun attraction dynamics"
        elif key == "stability":
            desc = "Saturn ties add long-term potential"
        elif key == "elemental_balance":
            desc = "Overall element distribution harmony"
        # Append percent to description
        pct = f"{int(round(score_norm * 100, 0))}%"
        desc_full = (desc + f" | {pct}") if desc else pct
        kpi_rows.append(KpiScoreRow(kpi=label, score=score_norm, description=desc_full))

    # Total score also normalized to 0..1
    total_raw = float(syn.get("total_score", 0.0))  # 0..10
    total_norm = round(total_raw / 10.0, 2)
    total_pct = int(round(total_norm * 100, 0))

    # Summary referencing strongest KPI and tightest aspects
    strongest_kpi = max(kpi_map.items(), key=lambda x: x[1])[0] if kpi_map else "n/a"
    aspects = syn.get("aspects", [])
    top_aspects = sorted(aspects, key=lambda a: a.get("orb", 99.0))[:3]
    top_str = ", ".join(f"{a['planet1']}-{a['aspect_type']}-{a['planet2']} (orb {a['orb']})" for a in top_aspects) if top_aspects else "None"
    # Baseline guidance
    baseline = syn.get("baseline", {"average": 5.0, "good": 7.0, "excellent": 8.0})
    summary = (
        f"Overall compatibility {total_raw:.2f}/10 ({total_pct}%). Strongest area: {strongest_kpi.replace('_',' ').title()}. "
        f"Top tight aspects: {top_str}. Baseline: avg~{baseline.get('average', 5)}/10, good~{baseline.get('good', 7)}/10, excellent~{baseline.get('excellent', 8)}/10."
    )

    return CompatibilityOut(
        data=CompatibilityData(
            kpis=kpi_rows,
            totalScore=total_norm,
            summary=summary,
        ),
    )


@router.post("/compat/group", response_model=GroupCompatibilityOut, tags=["Compatibility"], summary="Group compatibility analysis (up to 10 people)")
def compat_group(
    req: GroupCompatibilityIn = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "people": [
                        {"name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN","timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777},
                        {"name": "Riya","dateOfBirth": "1993-02-20","timeOfBirth": "06:10:00","placeOfBirth": "Delhi, IN","timeZone": "Asia/Kolkata","latitude": 28.6139,"longitude": 77.2090},
                        {"name": "Karan","dateOfBirth": "1990-11-02","timeOfBirth": "14:05:00","placeOfBirth": "Pune, IN","timeZone": "Asia/Kolkata","latitude": 18.5204,"longitude": 73.8567}
                    ],
                    "type": "Friendship Group",
                    "cursor": None
                },
            }
        },
    ),
) -> GroupCompatibilityOut:
    """Run advanced group synastry using services.synastry_group_services.

    The output flattens KPI data into GroupCompatibilityData schema:
    - pairwise rows: one row per pair (total score) + top KPI for context
    - groupHarmony: each KPI averaged, normalized to 0..1 scale
    - totalGroupScore: normalized to 0..1
    """
    # Delegate validation and shaping to the service helper to keep API thin
    try:
        # Cast req.type to supported literal type (validated inside service)
        api_data = sg_build_group_api_payload(req.people, req.type)  # type: ignore[arg-type]
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Group analysis failed: {e}")

    return GroupCompatibilityOut(
        data=GroupCompatibilityData(**api_data),
    )


@router.post("/compat/soulmate-finder", response_model=SoulmateOut, tags=["Compatibility"], summary="Soulmate finder (returns candidate DOBs)")
def soulmate_finder(
    payload: BirthPayload = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "name": "Amit",
                    "dateOfBirth": "1991-07-14",
                    "timeOfBirth": "22:35:00",
                    "placeOfBirth": "Mumbai, IN",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 19.0760,
                    "longitude": 72.8777,
                },
            }
        },
    ),
) -> SoulmateOut:
    # Dummy: suggest some date patterns near the birth year ± 3 years
    dob = dt.date.fromisoformat(payload.dateOfBirth)
    candidates = [
        dob.replace(year=max(1900, dob.year - 2)).isoformat(),
        dob.replace(year=max(1900, dob.year - 1)).isoformat(),
        dob.replace(year=dob.year + 1).isoformat(),
        dob.replace(year=dob.year + 2).isoformat(),
    ]
    return SoulmateOut(data=SoulmateData(datesOfBirth=candidates))


# --------------- Vedic Compatibility (Ashtakoota / Gun Milan) ---------------
@router.post(
    "/compat/ashtakoota",
    response_model=AshtakootaOut,
    tags=["Compatibility"],
    summary="Vedic Ashtakoota (Gun Milan) score and explanation",
)
def compat_ashtakoota(
    req: CompatibilityPairIn = Body(
        ...,
        openapi_examples={
            "sample": {
                "summary": "Sample",
                "value": {
                    "person1": {
                        "name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN",
                        "timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777
                    },
                    "person2": {
                        "name": "Riya","dateOfBirth": "1993-02-20","timeOfBirth": "06:10:00","placeOfBirth": "Delhi, IN",
                        "timeZone": "Asia/Kolkata","latitude": 28.6139,"longitude": 77.2090
                    },
                    "type": "Marriage"
                },
            }
        },
    ),
    ayanamsa: str = "lahiri",
    coordinate_system: str = "sidereal",
    strict_tradition: bool = True,
    use_exceptions: bool = False,
) -> AshtakootaOut:
    """Compute Vedic Gun Milan for two charts and return detailed breakdown plus a short explanation.

    Optional query parameters:
    - ayanamsa: lahiri|krishnamurti|raman (default: lahiri)
    - coordinate_system: sidereal|tropical (default: sidereal)
    - strict_tradition: keep integer scoring (default: True)
    - use_exceptions: apply Nadi exceptions where relevant (default: False)
    """
    # Extract raw dicts from Pydantic models
    p1 = req.person1.model_dump() if hasattr(req.person1, "model_dump") else req.person1.dict()
    p2 = req.person2.model_dump() if hasattr(req.person2, "model_dump") else req.person2.dict()

    result = compute_ashtakoota_score(
        p1,
        p2,
        ayanamsa=ayanamsa,
        coordinate_system=coordinate_system,
        strict_tradition=strict_tradition,
        use_exceptions=use_exceptions,
    )
    expl = explain_ashtakoota(result)

    return AshtakootaOut(data=AshtakootaData(result=result, explanation=expl))
