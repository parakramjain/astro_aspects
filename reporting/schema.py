from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ReportDataError(ValueError):
    """Raised when required report data is missing or invalid."""


class InputBlock(BaseModel):
    name: str
    dateOfBirth: str
    timeOfBirth: str
    placeOfBirth: str
    timeZone: str
    latitude: float
    longitude: float
    timePeriod: str
    reportStartDate: str


class TimelineItem(BaseModel):
    aspect: str
    aspectNature: Optional[str] = None

    startDate: str
    exactDate: str
    endDate: str

    # Can be dict like {"en":"...","hi":"..."} or empty
    description: Optional[Union[str, Dict[str, Any]]] = None

    # actionables, expected shape: {"applying": {"en":[],"hi":[]}, ...}
    keyPoints: Optional[Dict[str, Any]] = None

    # facets points, expected keys career/relationships/money/health_adj with localized values
    facetsPoints: Optional[Dict[str, Any]] = None

    # keywords might be localized dict or other structure
    keywords: Optional[Dict[str, Any]] = None


class TimelineBlock(BaseModel):
    items: List[TimelineItem] = Field(default_factory=list)
    aiSummary: Optional[str] = None


class DailyWeeklyBlock(BaseModel):
    shortSummary: Optional[Union[str, Dict[str, Any]]] = None
    areas: Optional[Dict[str, Any]] = None


class LifeEventItem(BaseModel):
    aspect: str
    eventType: Optional[str] = None
    aspectNature: Optional[str] = None

    timePeriod: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    exactDate: Optional[str] = None

    description: Optional[Union[str, Dict[str, Any], List[Any]]] = None


class ReportJson(BaseModel):
    input: InputBlock
    generatedAt: Optional[str] = None

    timeline: TimelineBlock
    dailyWeekly: DailyWeeklyBlock

    lifeEvents: Optional[List[LifeEventItem]] = None
    lifeEventsError: Optional[str] = None
