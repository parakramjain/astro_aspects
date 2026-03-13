from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _clean_string(value: str | None) -> str | None:
    if value is None:
        return None
    out = str(value).strip()
    return out or None


def _clean_list(values: List[str] | None, *, limit: int) -> List[str] | None:
    if values is None:
        return None
    seen: set[str] = set()
    out: List[str] = []
    for raw in values:
        text = _clean_string(raw)
        if not text:
            continue
        norm = text.casefold()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(text)
        if len(out) >= limit:
            break
    return out or None


class UserProfileContext(BaseModel):
    current_role_title: Optional[str] = None
    industry: Optional[str] = None
    experience_years: Optional[int] = Field(default=None, ge=0)
    target_roles: Optional[List[str]] = None
    strengths_top3: Optional[List[str]] = None
    gaps_top3: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    time_available_hours_per_week: Optional[int] = Field(default=None, ge=1, le=80)
    preferred_companies_or_sectors: Optional[List[str]] = None
    geo: Optional[str] = None
    career_stage: Optional[Literal[
        "early_career",
        "mid_career_specialist",
        "mid_career_leader",
        "senior_leader",
        "founder",
    ]] = None
    tone_preference: Optional[Literal["practical", "encouraging", "direct", "executive"]] = None

    @field_validator("current_role_title", "industry", "geo", mode="before")
    @classmethod
    def _trim_scalars(cls, value: object) -> object:
        return _clean_string(value if isinstance(value, str) or value is None else str(value))

    @field_validator("target_roles", mode="before")
    @classmethod
    def _clean_target_roles(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        return _clean_list([str(v) for v in value], limit=5)

    @field_validator("preferred_companies_or_sectors", mode="before")
    @classmethod
    def _clean_preferred(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        return _clean_list([str(v) for v in value], limit=5)

    @field_validator("strengths_top3", "gaps_top3", mode="before")
    @classmethod
    def _clean_top3(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        return _clean_list([str(v) for v in value], limit=3)

    @field_validator("constraints", mode="before")
    @classmethod
    def _clean_constraints(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        return _clean_list([str(v) for v in value], limit=10)
