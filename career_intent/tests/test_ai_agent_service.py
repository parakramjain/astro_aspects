from __future__ import annotations

import copy
import json

from career_intent.ai_agent.ai_agent_service import CareerTimingAIAgent


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
            "config_version": "1.0.0",
            "model_version": "career_intent_v2",
            "feature_flags": ["quality_v2"],
            "generation_ms": 9,
        },
        "score_breakdown": {
            "timing_strength": 70,
            "execution_stability": 72,
            "risk_pressure": 38,
            "growth_leverage": 67,
            "labels": ["timing_strength", "execution_stability", "risk_pressure", "growth_leverage"],
        },
        "insight_highlights": ["Execution stability is strong.", "Risk pressure is manageable."],
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


def test_agent_returns_same_schema_and_allows_text_rewrite_only():
    baseline = _baseline()

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    rewritten = copy.deepcopy(baseline)
    rewritten["career_intent_scores"][0]["short_reason"] = "Advancement potential is strong with disciplined weekly execution."
    rewritten["career_intent_scores"][0]["next_step"] = "Book a scope and impact alignment discussion with leadership this week."
    rewritten["astro_aspects"][0]["description"] = "This phase supports visible progress when execution remains structured and consistent."

    def llm_rewrite(_system_prompt: str, _user_prompt: str) -> str:
        return json.dumps(rewritten)

    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    output = agent.rewrite_insight({"any": "payload"})

    assert output["career_momentum_score"] == baseline["career_momentum_score"]
    assert output["metadata"]["deterministic_hash"] == baseline["metadata"]["deterministic_hash"]
    assert output["opportunity_window"]["start_date"] == baseline["opportunity_window"]["start_date"]
    assert output["career_intent_scores"][0]["short_reason"] != baseline["career_intent_scores"][0]["short_reason"]


def test_agent_retries_once_with_repair_prompt_when_first_output_invalid():
    baseline = _baseline()

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    repaired = copy.deepcopy(baseline)
    repaired["recommendation_summary"][0] = "Apply for high-impact outcomes during the opportunity window."

    calls = {"n": 0}

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "{ not valid json"
        return json.dumps(repaired)

    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    out = agent.rewrite_insight({})
    assert calls["n"] == 2
    assert out["career_momentum_score"] == baseline["career_momentum_score"]
    assert out["recommendation_summary"][0] == repaired["recommendation_summary"][0]


def test_agent_uses_compact_path_when_full_unavailable():
    baseline = _baseline()

    def fetch_compact(_request: dict) -> dict:
        return {"any": "compact"}

    def expand_compact(_compact: dict) -> dict:
        return copy.deepcopy(baseline)

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        return json.dumps(baseline)

    agent = CareerTimingAIAgent(
        llm_rewrite=llm_rewrite,
        fetch_compact_insight=fetch_compact,
        expand_compact_to_full=expand_compact,
    )
    out = agent.rewrite_insight({})
    assert out["metadata"]["request_id"] == "req-1"


def test_agent_profile_target_role_and_constraints_and_time_budget():
    baseline = _baseline()

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        return json.dumps(copy.deepcopy(baseline))

    profile = {
        "target_roles": ["GenAI Architect"],
        "constraints": ["No relocation"],
        "time_available_hours_per_week": 3,
    }
    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    out = agent.rewrite_insight({}, user_profile=profile)

    assert "GenAI Architect" in " ".join(row["next_step"] for row in out["career_intent_scores"])
    assert "relocation" not in " ".join(out["recommendation_summary"]).lower()
    assert all("under 60 minutes" in item.lower() for item in out["action_plan"]["now_to_opportunity_start"])


def test_profile_absence_keeps_legacy_compatible_behavior():
    baseline = _baseline()

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        return json.dumps(copy.deepcopy(baseline))

    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    out = agent.rewrite_insight({}, user_profile=None)
    assert out == baseline


def test_agent_repair_handles_missing_required_astro_aspect_fields():
    baseline = _baseline()
    for idx in range(1, 12):
        row = copy.deepcopy(baseline["astro_aspects"][0])
        row["aspect_name"] = f"Transit Test Aspect {idx}"
        baseline["astro_aspects"].append(row)

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    bad = copy.deepcopy(baseline)
    bad["astro_aspects"][10] = {
        "aspect_name": "Transit Jupiter Trine Natal Sun",
        "description": "Supports strategic decisions.",
    }
    bad["astro_aspects"][11] = {
        "aspect_name": "Transit Saturn Square Natal Mercury",
        "description": "Supports agentic AI projects.",
    }

    calls = {"n": 0}

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        calls["n"] += 1
        return json.dumps(bad)

    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    out = agent.rewrite_insight({})
    assert calls["n"] == 1
    assert out["astro_aspects"][10]["start_date"] == baseline["astro_aspects"][10]["start_date"]
    assert out["astro_aspects"][11]["impact_score"] == baseline["astro_aspects"][11]["impact_score"]
    assert out["recommendation_summary"][0] == baseline["recommendation_summary"][0]


def test_agent_raises_when_both_attempts_are_invalid_json():
    baseline = _baseline()
    for idx in range(1, 12):
        row = copy.deepcopy(baseline["astro_aspects"][0])
        row["aspect_name"] = f"Transit Test Aspect {idx}"
        baseline["astro_aspects"].append(row)

    def fetch_full(_request: dict) -> dict:
        return copy.deepcopy(baseline)

    def llm_rewrite(_system_prompt: str, _prompt: str) -> str:
        return "{ not valid json"

    agent = CareerTimingAIAgent(llm_rewrite=llm_rewrite, fetch_full_insight=fetch_full)
    try:
        agent.rewrite_insight({})
        assert False, "Expected rewrite_insight to fail when both attempts return invalid JSON"
    except ValueError as exc:
        text = str(exc)
        assert "Invalid JSON" in text
