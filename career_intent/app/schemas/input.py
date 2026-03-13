from __future__ import annotations

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from career_intent.app.schemas.user_profile import UserProfileContext

SUPPORTED_INTENTS = [
    "Job Change",
    "Promotion",
    "Entrepreneurship",
    "Skill Building",
    "Exploration / Discovery",
    "Networking / Positioning",
    "Side Project / Testing the Waters",
    "Transition / In Between",
]


class BirthPayloadIn(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Amit",
                    "dateOfBirth": "1983-03-28",
                    "timeOfBirth": "22:30:00",
                    "placeOfBirth": "Mumbai, IN",
                    "timeZone": "Asia/Kolkata",
                    "latitude": 19.076,
                    "longitude": 72.8777,
                    "lang_code": "en",
                }
            ]
        }
    }

    name: str
    dateOfBirth: str
    timeOfBirth: str
    placeOfBirth: str
    timeZone: str
    latitude: float
    longitude: float
    lang_code: Optional[str] = "en"


class TimeframeIn(BaseModel):
    months: Optional[int] = Field(default=None, ge=1, le=24)
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CareerInsightRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "birth_payload": {
                        "name": "Amit",
                        "dateOfBirth": "1983-03-28",
                        "timeOfBirth": "11:30:00",
                        "placeOfBirth": "Indore, IN",
                        "timeZone": "Asia/Kolkata",
                        "latitude": 22.7196,
                        "longitude": 75.8577,
                        "lang_code": "en",
                    },
                    "career_intent": "Promotion",
                    "timeframe": {"months": 1},
                    "user_profile": {
                        "current_role_title": "Senior Data Scientist and AI Specialist",
                        "industry": ["Aviation", "Retail"],
                        "experience_years": 10,
                        "target_roles": ["GenAI Architect"],
                        "strengths_top3": ["Python", "ML", "Agentic AI development"],
                        "gaps_top3": ["LLMOps", "System design", "Product thinking"],
                        "constraints": ["No relocation", "Evenings only"],
                        "time_available_hours_per_week": 6,
                        "preferred_companies_or_sectors": ["Airports", "Transportation", "Public sector"],
                        "geo": "Toronto",
                        "career_stage": "mid_career_leader",
                        "tone_preference": "practical",
                    },
                }
            ]
        }
    }

    birth_payload: BirthPayloadIn
    career_intent: Literal[
        "Job Change",
        "Promotion",
        "Entrepreneurship",
        "Skill Building",
        "Exploration / Discovery",
        "Networking / Positioning",
        "Side Project / Testing the Waters",
        "Transition / In Between",
    ]
    timeframe: Optional[TimeframeIn] = None
    user_profile: Optional[UserProfileContext] = None

    @field_validator("career_intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        if value not in SUPPORTED_INTENTS:
            raise ValueError("Unsupported career_intent")
        return value
