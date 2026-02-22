from __future__ import annotations
import datetime as dt
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# --------- Common ---------
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: Optional[str] = None


class ErrorEnvelope(BaseModel):
    code: str = Field(default="SERVER_ERROR")
    message: str
    details: Optional[List[ErrorDetail]] = None


class ErrorResponse(BaseModel):
    error: ErrorEnvelope


# --------- Inputs ---------
class BirthPayload(BaseModel):
    """Basic birth details used across requests."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "Amit",
                "dateOfBirth": "1991-07-14",
                "timeOfBirth": "22:35:00",
                "placeOfBirth": "Mumbai, IN",
                "timeZone": "Asia/Kolkata",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "lang_code": "en"
            }
        ]
    })

    name: str = Field(..., description="Full name of the person.", examples=["Amit"]) 
    dateOfBirth: str = Field(..., description="Birth date in ISO format YYYY-MM-DD.", examples=["1991-07-14"])  # YYYY-MM-DD
    timeOfBirth: str = Field(..., description="Birth time in 24h format HH:MM or HH:MM:SS.", examples=["22:35:00"])  # HH:MM[:SS]
    placeOfBirth: str = Field(..., description="Human-readable place name (city, country).", examples=["Mumbai, IN"]) 
    timeZone: str = Field(..., description="IANA timezone for the place of birth.", examples=["Asia/Kolkata"]) 
    latitude: float = Field(..., description="Latitude in decimal degrees (north positive).", examples=[19.0760])
    longitude: float = Field(..., description="Longitude in decimal degrees (east positive).", examples=[72.8777])
    lang_code: Optional[str] = Field(default="en", description="Optional ISO language code for localized responses.", examples=["en"])


class PersonPayload(BaseModel):
    """A person's birth profile for compatibility/group inputs."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "Riya",
                "dateOfBirth": "1993-02-20",
                "timeOfBirth": "06:10:00",
                "placeOfBirth": "Delhi, IN",
                "timeZone": "Asia/Kolkata",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "lang_code": "en"
            }
        ]
    })

    name: str = Field(..., description="Full name of the person.", examples=["Riya"]) 
    dateOfBirth: str = Field(..., description="Birth date in ISO format YYYY-MM-DD.", examples=["1993-02-20"]) 
    timeOfBirth: str = Field(..., description="Birth time in 24h format HH:MM or HH:MM:SS.", examples=["06:10:00"]) 
    placeOfBirth: str = Field(..., description="Human-readable place name (city, country).", examples=["Delhi, IN"]) 
    timeZone: str = Field(..., description="IANA timezone for the place of birth.", examples=["Asia/Kolkata"]) 
    latitude: float = Field(..., description="Latitude in decimal degrees (north positive).", examples=[28.6139])
    longitude: float = Field(..., description="Longitude in decimal degrees (east positive).", examples=[77.2090])
    lang_code: Optional[str] = Field(default="en", description="Optional ISO language code for localized responses.", examples=["en"])


class CompatibilityPairIn(BaseModel):
    """Two people and the compatibility context/type."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "person1": {
                    "name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN",
                    "timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777,"lang_code": "en"
                },
                "person2": {
                    "name": "Riya","dateOfBirth": "1993-02-20","timeOfBirth": "06:10:00","placeOfBirth": "Delhi, IN",
                    "timeZone": "Asia/Kolkata","latitude": 28.6139,"longitude": 77.2090,"lang_code": "en"
                },
                "type": "General"
            }
        ]
    })

    person1: PersonPayload = Field(..., description="First person (subject)")
    person2: PersonPayload = Field(..., description="Second person (partner)")
    type: str = Field(..., description='Compatibility context. Allowed: "Marriage","Friendship","Professional","General".', examples=["General"]) 


class GroupCompatibilityIn(BaseModel):
    """Group compatibility request (2–10 people)."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "people": [
                    {"name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN","timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777,"lang_code": "en"},
                    {"name": "Riya","dateOfBirth": "1993-02-20","timeOfBirth": "06:10:00","placeOfBirth": "Delhi, IN","timeZone": "Asia/Kolkata","latitude": 28.6139,"longitude": 77.2090,"lang_code": "en"}
                ],
                "type": "Professional",
                "cursor": None
            }
        ]
    })

    people: List[PersonPayload] = Field(..., description="List of people (min 2, max 10)")
    type: str = Field(..., description='Group type. Allowed: "Friendship Group","Professional Team","Sport Team","Family","Relative".', examples=["Professional Team"]) 
    cursor: Optional[str] = Field(default=None, description="Optional cursor for pagination.")


class TimelineRequest(BirthPayload):
    """Timeline report request for a given period starting at a specific date."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN",
                "timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777,"lang_code": "en",
                "timePeriod": "6M","reportStartDate": "2025-11-01","cursor": None
            }
        ]
    })

    timePeriod: str = Field(..., description='Time span for the report. Allowed: "1Y","6M","1M".', examples=["6M"]) 
    reportStartDate: str = Field(..., description="Start date (YYYY-MM-DD). Commonly the first of the month.", examples=["2025-11-01"])  # date
    cursor: Optional[str] = Field(default=None, description="Optional cursor for pagination.")


class DailyWeeklyRequest(BirthPayload):
    """Daily/Weekly short forecast request."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "Amit","dateOfBirth": "1991-07-14","timeOfBirth": "22:35:00","placeOfBirth": "Mumbai, IN",
                "timeZone": "Asia/Kolkata","latitude": 19.0760,"longitude": 72.8777,"lang_code": "en", "timePeriod": "1W",
                "mode": "DAILY"
            }
        ]
    })

    mode: str = Field(default="DAILY", description='Mode of the report. Allowed: "DAILY","WEEKLY".', examples=["DAILY"])  # DAILY | WEEKLY


# --------- Outputs ---------
class PlanetEntry(BaseModel):
    planetName: str
    planetSign: str
    planetDegree: float
    houseNumber: int
    houseName: Optional[str] = None
    houseSign: Optional[str] = None


class NatalChartData(BaseModel):
    planets: List[PlanetEntry]


class NatalChartOut(BaseModel):
    data: NatalChartData


class DignityRow(BaseModel):
    planet: str
    rulership: bool
    exaltation: bool
    detriment: bool
    fall: bool
    essentialScore: float
    notes: Optional[str] = None


class DignitiesData(BaseModel):
    table: List[DignityRow]


class DignitiesOut(BaseModel):
    data: DignitiesData


class NatalAspectItem(BaseModel):
    aspect: str
    angle: float = Field(..., description="Angular separation in degrees for the aspect.")
    dist: float = Field(..., description="Distance from exact aspect in degrees.")
    strength: float
    characteristics: Dict[str, Any] = Field(default_factory=dict, description="Mapping of characteristic keys to values.")


class NatalAspectsOut(BaseModel):
    data: List[NatalAspectItem]


class KpiItem(BaseModel):
    name: str
    shortDescription: str


class NatalCharacteristicsData(BaseModel):
    description: Dict[str, Any]
    # kpis: List[KpiItem]


class NatalCharacteristicsOut(BaseModel):
    data: NatalCharacteristicsData

class LifeEventPayload(BirthPayload):
    start_date: Optional[str]
    horizon_days: int

class LifeEvent(BaseModel):
    aspect: str
    eventType: str  # MAJOR | MINOR
    aspectNature: str  # Positive | Negative
    timePeriod: str
    startDate: str
    endDate: str
    exactDate: str
    description: str


class LifeEventsOut(BaseModel):
    data: List[LifeEvent]


class TimelineItem(BaseModel):
    aspect: str
    aspectNature: str  # Positive | Negative
    startDate: str
    exactDate: str
    endDate: str
    description: str
    # keyPoints: Optional[Dict[str, Any]] = None
    facetsPoints: Optional[Dict[str, Any]] = None
    # keywords: Optional[Dict[str, Any]] = None


class TimelineData(BaseModel):
    items: List[TimelineItem]
    aiSummary: Optional[str] = None


class TimelineOut(BaseModel):
    data: TimelineData


class DailyArea(BaseModel):
    keyArea: str
    shortDescription: str
    # color: str  # GREEN | RED | AMBER


class DailyWeeklyData(BaseModel):
    shortSummary: str

class DailyWeeklyOut(BaseModel):
    data: DailyWeeklyData


class UpcomingEventWindow(BaseModel):
    startDate: str
    exactDate: str
    leaveDate: str


class UpcomingEventRow(BaseModel):
    aspect: str
    timePeriod: UpcomingEventWindow
    lifeEvent: Optional[str] = None
    shortDescription: Optional[str] = None
    category: Optional[str] = None  # POSITIVE | NEGATIVE


class UpcomingEventsOut(BaseModel):
    data: List[UpcomingEventRow]


class UpcomingCalendarEvent(BaseModel):
    aspect: str
    aspectNature: str  # Positive | Negative
    description: Any


class UpcomingCalendarDay(BaseModel):
    date: str  # YYYY-MM-DD
    events: List[UpcomingCalendarEvent]


class UpcomingEventsCalendarOut(BaseModel):
    """Calendar-friendly daily expansion of upcoming life events."""

    data: List[UpcomingCalendarDay]
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None


class KpiScoreRow(BaseModel):
    kpi: str
    score: float
    description: Optional[str] = None


class CompatibilityData(BaseModel):
    kpis: List[KpiScoreRow]
    totalScore: float
    summary: str


class CompatibilityOut(BaseModel):
    data: CompatibilityData


class PairwiseRow(BaseModel):
    person1: str
    person2: str
    kpi: str
    score: float
    description: Optional[str] = None


class GroupCompatibilityData(BaseModel):
    pairwise: List[PairwiseRow]
    groupHarmony: List[KpiScoreRow]
    totalGroupScore: float


class GroupCompatibilityOut(BaseModel):
    data: GroupCompatibilityData


class SoulmateData(BaseModel):
    datesOfBirth: List[str]


class SoulmateOut(BaseModel):
    data: SoulmateData


# --------- Vedic Ashtakoota (Gun Milan) ---------
class AshtakootaData(BaseModel):
    """Container for Vedic Ashtakoota result and explanation string.

    'result' mirrors the structure returned by compute_ashtakoota_score and is kept as
    Dict[str, Any] to remain forward-compatible.
    """
    result: Dict[str, Any]
    explanation: str


class AshtakootaOut(BaseModel):
    data: AshtakootaData

# ----------------- Group Synastry Extended Models (New) -----------------
class GroupSettings(BaseModel):
    """Settings for group compatibility computations (mirrors service module).

    These settings are kept lightweight; heavy runtime dicts (aspect/orb maps)
    are injected at call time by the service layer.
    """
    aspect_weights: Dict[str, float] = Field(default_factory=dict)
    orbs: Dict[str, Any] = Field(default_factory=dict)
    planet_weights: Dict[str, float] = Field(default_factory=dict)
    type_kpi_weights: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    enable_network: bool = True
    max_group_for_full_matrix: int = 20
    sample_pairs_if_large: bool = True
    random_seed: Optional[int] = 42


class PairwiseResult(BaseModel):
    """Pairwise KPI outcome for two people in a group context."""
    person1: str
    person2: str
    kpi_scores: Dict[str, float]
    total_pair_score: float
    description: str


class GroupKPI(BaseModel):
    """Aggregated KPI score across all group pairs."""
    kpi: str
    score: float
    description: str


class GroupResult(BaseModel):
    """Full group compatibility result including pairwise and harmony KPIs."""
    pairwise: List[PairwiseResult]
    group_harmony: List[GroupKPI]
    total_group_score: float
    short_summary: str
    card_payload: Dict[str, Any]
