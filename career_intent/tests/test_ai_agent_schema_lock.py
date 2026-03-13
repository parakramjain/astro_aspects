from __future__ import annotations

import copy

import pytest

from career_intent.ai_agent.schema_lock import (
    MUTABLE_PATH_PATTERNS,
    apply_text_fields,
    assert_schema_and_values_unchanged,
    extract_text_fields,
)


def _baseline() -> dict:
    return {
        "career_momentum_score": 72,
        "opportunity_window": {
            "start_date": "2026-07-10",
            "end_date": "2026-08-12",
            "score": 68,
            "top_drivers": ["Execution rhythm", "Stakeholder alignment"],
            "drivers_detail": [
                {
                    "driver_label": "Execution rhythm",
                    "category": "Opportunity",
                    "polarity": "positive",
                    "impact_score": 68,
                    "evidence_snippet": "Strong pace supports timely outcomes.",
                }
            ],
        },
        "caution_window": {
            "start_date": "2026-08-13",
            "end_date": "2026-09-02",
            "score": 52,
            "top_drivers": ["Execution drag"],
            "drivers_detail": [
                {
                    "driver_label": "Execution drag",
                    "category": "Stability",
                    "polarity": "negative",
                    "impact_score": 52,
                    "evidence_snippet": "Workload constraints may slow delivery.",
                }
            ],
        },
        "career_intent_scores": [
            {
                "intent_name": "Promotion",
                "score": 66,
                "short_reason": "Current profile supports advancement with disciplined execution.",
                "recommended_window": "opportunity",
                "next_step": "Negotiate measurable impact targets.",
            },
            {
                "intent_name": "Skill Building",
                "score": 61,
                "short_reason": "Capability growth remains favorable with consistent practice.",
                "recommended_window": "neutral",
                "next_step": "Build one portfolio-grade output.",
            },
        ],
        "recommendation_summary": [
            "Apply focused effort during opportunity window.",
            "Review risks before major commitments.",
        ],
        "metadata": {
            "timeframe_start": "2026-07-01",
            "timeframe_end": "2026-12-31",
            "generated_at": "2026-03-05T10:00:00+00:00",
            "version": "0.1.0",
            "deterministic_hash": "abc",
            "request_id": "req-1",
            "fallback_flags": [],
        },
        "score_breakdown": {
            "timing_strength": 70,
            "execution_stability": 72,
            "risk_pressure": 38,
            "growth_leverage": 67,
            "labels": ["timing_strength", "execution_stability", "risk_pressure", "growth_leverage"],
        },
        "insight_highlights": ["Execution stability is strong."],
        "window_guidance": {
            "opportunity_actions": ["Align on scope and timelines."],
            "caution_actions": ["Limit non-essential changes."],
        },
        "confidence": {"overall": 74, "drivers_coverage": 67, "data_quality_flags": []},
        "window_quality": {"opportunity_window_quality": 69, "caution_window_quality": 58},
        "action_plan": {
            "now_to_opportunity_start": ["Prepare decision brief."],
            "during_opportunity": ["Execute top-priority goals."],
            "during_caution": ["Pause non-critical commitments."],
        },
        "astro_aspects": [
            {
                "aspect_name": "Transit Jupiter Trine Natal Sun",
                "description": "Supports visible progress through constructive effort.",
                "start_date": "2026-07-10",
                "end_date": "2026-08-12",
                "exact_date": "2026-07-20",
                "impact_score": 72,
            }
        ],
    }


def test_extract_and_apply_text_fields():
    base = _baseline()
    extracted = extract_text_fields(base)
    assert "career_intent_scores[0].short_reason" in extracted
    assert "opportunity_window.top_drivers[0]" in extracted

    updates = {
        "career_intent_scores[0].short_reason": "Advancement fit is strong with consistent execution.",
        "astro_aspects[0].description": "Constructive momentum supports visible progress this phase.",
    }
    patched = apply_text_fields(base, updates)
    assert patched["career_intent_scores"][0]["short_reason"] == updates["career_intent_scores[0].short_reason"]
    assert patched["astro_aspects"][0]["description"] == updates["astro_aspects[0].description"]
    assert patched["career_momentum_score"] == base["career_momentum_score"]


def test_schema_lock_allows_only_allowlisted_strings():
    base = _baseline()
    rewritten = copy.deepcopy(base)
    rewritten["career_intent_scores"][0]["short_reason"] = "Clear advancement potential with disciplined outcomes."
    assert_schema_and_values_unchanged(base, rewritten, MUTABLE_PATH_PATTERNS)


def test_schema_lock_blocks_numeric_and_order_changes():
    base = _baseline()

    bad_numeric = copy.deepcopy(base)
    bad_numeric["score_breakdown"]["timing_strength"] = 99
    with pytest.raises(ValueError):
        assert_schema_and_values_unchanged(base, bad_numeric, MUTABLE_PATH_PATTERNS)

    bad_order = copy.deepcopy(base)
    bad_order["career_intent_scores"] = list(reversed(bad_order["career_intent_scores"]))
    with pytest.raises(ValueError):
        assert_schema_and_values_unchanged(base, bad_order, MUTABLE_PATH_PATTERNS)


def test_schema_lock_blocks_disallowed_string_changes():
    base = _baseline()
    bad = copy.deepcopy(base)
    bad["metadata"]["request_id"] = "req-changed"
    with pytest.raises(ValueError):
        assert_schema_and_values_unchanged(base, bad, MUTABLE_PATH_PATTERNS)
