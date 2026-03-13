from __future__ import annotations

import json

from career_intent.app.core.compact_serializer import CompactSerializer


def _sample_full() -> dict:
    return {
        "career_momentum_score": 74,
        "score_breakdown": {
            "timing_strength": 72,
            "execution_stability": 74,
            "risk_pressure": 35,
            "growth_leverage": 67,
        },
        "opportunity_window": {
            "start_date": "2026-07-20",
            "end_date": "2026-08-17",
            "score": 66,
            "top_drivers": ["Stakeholder alignment", "Execution rhythm", "Growth capacity"],
        },
        "caution_window": {
            "start_date": "2026-08-10",
            "end_date": "2026-08-25",
            "score": 58,
            "top_drivers": ["Execution drag", "Communication friction"],
        },
        "career_intent_scores": [
            {"intent_name": "Promotion", "score": 68, "recommended_window": "opportunity", "next_step": "Negotiate measurable impact targets with leadership."},
            {"intent_name": "Skill Building", "score": 63, "recommended_window": "neutral", "next_step": "Build one portfolio-grade proof of work."},
            {"intent_name": "Job Change", "score": 66, "recommended_window": "opportunity", "next_step": "Apply to selective roles with role-fit evidence."},
            {"intent_name": "Networking / Positioning", "score": 60, "recommended_window": "opportunity", "next_step": "Schedule five high-signal outreach conversations."},
        ],
        "action_plan": {
            "now_to_opportunity_start": ["Prepare decision brief.", "Align execution metrics."],
            "during_opportunity": ["Execute highest-impact work.", "Negotiate scope and ownership."],
            "during_caution": ["Pause non-critical commitments.", "Reduce workload fragmentation."],
        },
        "astro_aspects": [
            {
                "aspect_name": "Transit Jupiter Trine Natal Sun",
                "description": "A period supportive of expansion, confidence, and visible progress through constructive efforts.",
                "start_date": "2026-07-10",
                "end_date": "2026-08-12",
                "exact_date": "2026-07-20",
                "impact_score": 72,
            },
            {
                "aspect_name": "Transit Saturn Square Natal Mercury",
                "description": "Delays and structured effort are required; avoid explosives and firearms in risky operations.",
                "start_date": "2026-08-15",
                "end_date": "2026-08-16",
                "exact_date": "2026-08-15",
                "impact_score": 65,
            },
            {
                "aspect_name": "Transit Venus Sextile Natal Moon",
                "description": "Supports smoother collaboration and better emotional pacing across commitments.",
                "start_date": "2026-08-18",
                "end_date": "2026-08-23",
                "exact_date": "2026-08-20",
                "impact_score": 58,
            },
        ],
        "metadata": {
            "timeframe_start": "2026-03-01",
            "timeframe_end": "2026-08-31",
            "request_id": "req-1",
            "deterministic_hash": "hash-1",
            "fallback_flags": ["parser_fallback"],
        },
        "insight_highlights": ["Long verbose text field for full mode only"],
        "window_guidance": {"opportunity_actions": ["x"], "caution_actions": ["y"]},
        "recommendation_summary": ["very long narrative summary"],
    }


def _serializer(top_intents: int = 3, top_aspects: int = 10) -> CompactSerializer:
    return CompactSerializer(
        thresholds={
            "compact": {
                "top_intents": top_intents,
                "top_aspects": top_aspects,
                "min_aspect_days": 3,
                "keep_high_impact_threshold": 70,
                "max_desc_len": 90,
            }
        },
        driver_map={
            "drivers": [
                {"key": "stakeholder_alignment", "label": "Stakeholder alignment"},
                {"key": "execution_rhythm", "label": "Execution rhythm"},
                {"key": "growth_capacity", "label": "Growth capacity"},
                {"key": "execution_drag", "label": "Execution drag"},
                {"key": "communication_friction", "label": "Communication friction"},
            ]
        },
        driver_catalog={
            "catalog": {
                "drv_stakeholder_alignment": "Stakeholder alignment",
                "drv_execution_rhythm": "Execution rhythm",
                "drv_growth_capacity": "Growth capacity",
                "drv_execution_drag": "Execution drag",
                "drv_communication_friction": "Communication friction",
            }
        },
    )


def test_compact_has_required_fields():
    compact = _serializer().serialize(_sample_full(), config_version="0.1.0")
    assert set(compact.keys()) == {"v", "tf", "cms", "sd", "ow", "cw", "ti", "ap", "ax", "md"}
    assert set(compact["tf"].keys()) == {"s", "e"}
    assert set(compact["sd"].keys()) == {"t", "st", "r", "g"}
    assert set(compact["ow"].keys()) == {"s", "e", "sc", "d"}
    assert set(compact["cw"].keys()) == {"s", "e", "sc", "d"}
    assert set(compact["ap"].keys()) == {"pre", "opp", "cau"}
    assert set(compact["md"].keys()) == {"id", "h", "ff"}


def test_compact_reduces_payload_length_heuristically():
    full = _sample_full()
    compact = _serializer().serialize(full, config_version="0.1.0")
    full_len = len(json.dumps(full, separators=(",", ":")))
    compact_len = len(json.dumps(compact, separators=(",", ":")))
    assert compact_len < full_len


def test_ordering_and_deterministic_truncation():
    serializer = _serializer()
    full = _sample_full()
    c1 = serializer.serialize(full, config_version="0.1.0")
    c2 = serializer.serialize(full, config_version="0.1.0")
    assert c1 == c2
    assert c1["ax"][0]["sc"] >= c1["ax"][-1]["sc"]
    assert all(len(row["ds"]) <= 90 for row in c1["ax"])
    assert all("…" not in row["ds"] for row in c1["ax"])
    assert all(row["ds"].count(".") <= 1 for row in c1["ax"])


def test_top_n_intents_and_aspects_limits_applied():
    compact = _serializer(top_intents=3, top_aspects=1).serialize(_sample_full(), config_version="0.1.0")
    assert len(compact["ti"]) == 3
    assert len(compact["ax"]) == 1


def test_aspect_filter_and_safety_sanitization():
    compact = _serializer().serialize(_sample_full(), config_version="0.1.0")
    names = [row["n"] for row in compact["ax"]]
    assert "Transit Saturn Square Natal Mercury" not in names
    text_dump = " ".join(row["ds"] for row in compact["ax"])
    assert "firearms" not in text_dump.lower()
    assert "explosives" not in text_dump.lower()


def test_driver_ids_prefixed_and_categories_coded():
    compact = _serializer().serialize(_sample_full(), config_version="0.1.0")
    assert all(item.startswith("drv_") for item in compact["ow"]["d"])
    assert all(item.startswith("drv_") for item in compact["cw"]["d"])
    assert all(row["c"] in {"g", "e", "s", "p", "l", "o"} for row in compact["ax"])
