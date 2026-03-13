from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DriverDetailOut(BaseModel):
    driver_label: str
    category: str
    polarity: str
    impact_score: int = Field(ge=0, le=100)
    evidence_snippet: str


class WindowOut(BaseModel):
    start_date: str
    end_date: str
    score: int = Field(ge=0, le=100)
    top_drivers: List[str]
    drivers_detail: Optional[List[DriverDetailOut]] = None


class IntentScoreOut(BaseModel):
    intent_name: str
    score: int = Field(ge=0, le=100)
    short_reason: str
    recommended_window: Optional[str] = None
    next_step: Optional[str] = None


class ScoreBreakdownOut(BaseModel):
    timing_strength: int = Field(ge=0, le=100)
    execution_stability: int = Field(ge=0, le=100)
    risk_pressure: int = Field(ge=0, le=100)
    growth_leverage: int = Field(ge=0, le=100)
    labels: Optional[List[str]] = None


class WindowGuidanceOut(BaseModel):
    opportunity_actions: List[str]
    caution_actions: List[str]


class ConfidenceOut(BaseModel):
    overall: int = Field(ge=0, le=100)
    drivers_coverage: int = Field(ge=0, le=100)
    data_quality_flags: List[str] = Field(default_factory=list)


class WindowQualityOut(BaseModel):
    opportunity_window_quality: int = Field(ge=0, le=100)
    caution_window_quality: int = Field(ge=0, le=100)


class ActionPlanOut(BaseModel):
    now_to_opportunity_start: List[str]
    during_opportunity: List[str]
    during_caution: List[str]


class AstroAspectOut(BaseModel):
    aspect_name: str
    description: str
    start_date: str
    end_date: str
    exact_date: str
    impact_score: int = Field(ge=0, le=100)


class MetadataOut(BaseModel):
    timeframe_start: str
    timeframe_end: str
    generated_at: str
    version: str
    deterministic_hash: str
    request_id: str
    fallback_flags: List[str] = Field(default_factory=list)
    config_version: Optional[str] = None
    model_version: Optional[str] = None
    feature_flags: Optional[List[str]] = None
    generation_ms: Optional[int] = None


class CareerInsightOut(BaseModel):
    career_momentum_score: int = Field(ge=0, le=100)
    opportunity_window: WindowOut
    caution_window: WindowOut
    career_intent_scores: List[IntentScoreOut]
    recommendation_summary: List[str]
    metadata: MetadataOut
    score_breakdown: Optional[ScoreBreakdownOut] = None
    insight_highlights: Optional[List[str]] = None
    window_guidance: Optional[WindowGuidanceOut] = None
    confidence: Optional[ConfidenceOut] = None
    window_quality: Optional[WindowQualityOut] = None
    action_plan: Optional[ActionPlanOut] = None
    astro_aspects: Optional[List[AstroAspectOut]] = None
