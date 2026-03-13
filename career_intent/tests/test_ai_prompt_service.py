from __future__ import annotations

from career_intent.ai_agent.ai_prompt_service import build_system_prompt, build_user_prompt


def test_system_prompt_contains_profile_safety_constraints():
    prompt = build_system_prompt(["career_intent_scores[*].next_step"])
    assert "Use user_profile ONLY" in prompt
    assert "Do NOT change any deterministic analytical fields" in prompt or "Keep ALL numbers, dates" in prompt


def test_user_prompt_includes_user_profile_when_present():
    full_json = {"a": 1}
    profile = {"target_roles": ["GenAI Architect"], "constraints": ["No relocation"]}
    prompt = build_user_prompt(full_json, profile)
    assert "User profile:" in prompt
    assert "GenAI Architect" in prompt
    assert "No relocation" in prompt
