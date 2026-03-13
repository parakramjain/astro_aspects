from __future__ import annotations

import json
from typing import Any, Dict, List


def _json_dump(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def build_system_prompt(allowlist_paths: List[str]) -> str:
    allowlist = "\n".join(f"- {path}" for path in allowlist_paths)
    return (
        "You are rewriting a career insight/report JSON to make it personally relevant and easier to act on.\n"
        "Use user_profile ONLY to tailor language, examples, next steps, recommendations, and action items.\n"
        "If profile fields are missing, stay generic and do not guess.\n"
        "Return valid JSON only (no markdown, no comments, no extra text).\n\n"
        "HARD CONSTRAINTS (non-negotiable)\n"
        "1) Keep the exact same JSON keys and nested structure.\n"
        "2) Keep ALL numbers, dates, ordering, metadata, hashes, request_id, flags, scores unchanged.\n"
        "3) Change ONLY allowlisted string paths.\n"
        "4) Keep list lengths unchanged.\n"
        "5) No new fields. No removed fields.\n"
        "6) Do NOT invent facts not present in JSON or user_profile.\n"
        "7) Do NOT infer employer, salary, education, certifications, or family situation unless explicitly provided.\n\n"
        "TONE + PERSONAL CONNECTION RULES\n"
        "- Write directly to the person using 'you' (second-person).\n"
        "- Be specific using timeframe, windows, scores, intents/drivers, and user_profile context if provided.\n"
        "- Use profile context to tailor recommendations and action steps to role and goals.\n"
        "- Avoid generic phrasing like 'review your tasks' or vague advice.\n"
        "- Keep language simple and confident. No buzzwords.\n"
        "- Avoid astrology terminology in all rewritten text.\n\n"
        "PERSONALIZATION QUALITY RULES\n"
        "- Align recommendations with target_roles when provided.\n"
        "- Leverage strengths_top3 and address gaps_top3 in action wording when available.\n"
        "- Respect constraints and available time; do not suggest actions that violate constraints.\n"
        "- Adapt tone to tone_preference when provided.\n\n"
        "CONTENT QUALITY RULES\n"
        "- recommendation_summary: 4–7 bullets, each starts with a strong verb, each anchored to an actual date range.\n"
        "- No duplicate recommendations across recommendation_summary, action_plan, and window_guidance.\n"
        "- short_reason: exactly ONE sentence, intent-specific, references relevant scores by meaning (not necessarily repeating all numbers).\n"
        "- next_step: exactly ONE sentence, concrete and measurable (quantity, deliverable, or checkpoint), anchored to window timing.\n"
        "- opportunity/caution drivers: keep as short labels; avoid repeating the same phrasing.\n"
        "- evidence_snippet and astro_aspects.description: ONE sentence, <= 140 characters, plain language, no fear, no absolutes.\n\n"
        "SAFETY + SENSITIVITY\n"
        "- Never guarantee outcomes.\n"
        "- Use supportive language in caution periods: 'reduce risk', 'slow down', 'double-check', not 'bad time' or 'failure'.\n\n"
        "ALLOWLISTED JSON PATHS (the ONLY places you may edit)\n"
        f"{allowlist}\n\n"
        "OUTPUT REQUIREMENT\n"
        "- Output MUST be the full JSON object with only allowlisted strings rewritten.\n"
        "- Do not change whitespace in keys, do not re-order lists, do not reformat numbers/dates.\n"
    )


def build_user_prompt(full_json: Dict[str, Any], user_profile: Dict[str, Any] | None = None) -> str:
    profile_payload = user_profile or {}
    return (
        "Task: Rewrite allowed text fields to feel more personally relevant and actionable for this individual.\n"
        "Use the user_profile only to tailor wording, recommendations, and next steps.\n"
        "Do not change scores, dates, windows, metadata, ordering, keys, hashes, or non-allowlisted fields.\n"
        "Do not invent missing information.\n"
        "Avoid astrology terminology.\n\n"
        "Quality checklist you must satisfy:\n"
        "- recommendation_summary: strong verbs + date-anchored + non-duplicative\n"
        "- next_step: measurable + tied to the window\n"
        "- evidence_snippet/astro_aspects.description: <= 140 chars, one sentence\n\n"
        "Return the full JSON only.\n\n"
        "User profile:\n"
        f"{_json_dump(profile_payload)}\n\n"
        "Original JSON:\n"
        f"{_json_dump(full_json)}"
    )


def build_repair_prompt(
    *,
    original_json: Dict[str, Any],
    user_profile: Dict[str, Any] | None,
    bad_output: str,
    violations: str,
    allowlist_paths: List[str],
) -> str:
    allowlist = "\n".join(f"- {path}" for path in allowlist_paths)
    return (
        "Repair required. Previous output violated schema/value lock.\n"
        f"Violations: {violations}\n"
        "Return corrected JSON only. Keep exact original structure and all non-allowlisted values identical.\n"
        "Allowed paths:\n"
        f"{allowlist}\n"
        "User profile:\n"
        f"{_json_dump(user_profile or {})}\n"
        "Original JSON:\n"
        f"{_json_dump(original_json)}\n"
        "Previous invalid output:\n"
        f"{bad_output}"
    )
