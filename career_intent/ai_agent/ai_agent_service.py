from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from career_intent.ai_agent.ai_models import AIRewriteRequest
from career_intent.ai_agent.ai_prompt_service import build_repair_prompt, build_system_prompt, build_user_prompt
from career_intent.ai_agent.schema_lock import (
    MUTABLE_PATH_PATTERNS,
    apply_text_fields,
    assert_schema_and_values_unchanged,
    extract_text_fields,
)
from career_intent.app.schemas.output import CareerInsightOut


class CareerTimingAIAgent:
    def __init__(
        self,
        *,
        llm_rewrite: Callable[[str, str], str],
        fetch_full_insight: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        fetch_compact_insight: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        expand_compact_to_full: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        allowlist_paths: Optional[List[str]] = None,
    ):
        self.llm_rewrite = llm_rewrite
        self.fetch_full_insight = fetch_full_insight
        self.fetch_compact_insight = fetch_compact_insight
        self.expand_compact_to_full = expand_compact_to_full
        self.allowlist_paths = allowlist_paths or list(MUTABLE_PATH_PATTERNS)

    def _get_baseline(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.fetch_full_insight is not None:
            return self.fetch_full_insight(request_payload)

        if self.fetch_compact_insight is not None and self.expand_compact_to_full is not None:
            compact = self.fetch_compact_insight(request_payload)
            return self.expand_compact_to_full(compact)

        raise ValueError("No baseline insight source configured")

    def _parse_llm_json(self, raw_text: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from LLM: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM output must be a JSON object")
        return parsed

    def _validate_rewrite(self, original: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validated = CareerInsightOut.model_validate(candidate)
        except ValidationError as exc:
            raise ValueError(f"Pydantic validation failed: {exc}") from exc

        normalized = validated.model_dump()
        assert_schema_and_values_unchanged(original, normalized, self.allowlist_paths)
        return normalized

    def _merge_allowlisted_text(self, baseline: Dict[str, Any], llm_candidate: Dict[str, Any]) -> Dict[str, Any]:
        updates = extract_text_fields(llm_candidate)
        merged = apply_text_fields(baseline, updates)
        return merged

    def _apply_profile_guardrails(self, payload: Dict[str, Any], user_profile: Dict[str, Any] | None) -> Dict[str, Any]:
        if not user_profile:
            return payload

        out = json.loads(json.dumps(payload))
        target_roles = [str(x).strip() for x in (user_profile.get("target_roles") or []) if str(x).strip()]
        constraints = [str(x).strip().lower() for x in (user_profile.get("constraints") or []) if str(x).strip()]
        gaps = [str(x).strip() for x in (user_profile.get("gaps_top3") or []) if str(x).strip()]
        strengths = [str(x).strip() for x in (user_profile.get("strengths_top3") or []) if str(x).strip()]
        time_hours = user_profile.get("time_available_hours_per_week")

        target_text = target_roles[0] if target_roles else ""
        if target_text:
            for row in out.get("career_intent_scores", []):
                next_step = str(row.get("next_step", "")).strip()
                if next_step and target_text.lower() not in next_step.lower():
                    row["next_step"] = f"{next_step.rstrip('.')} for {target_text}."

            recs = out.get("recommendation_summary") or []
            if recs:
                recs[0] = f"Prioritize actions that move you toward {target_text} during the active opportunity window."

        if gaps:
            ap = out.get("action_plan") or {}
            pre = ap.get("now_to_opportunity_start") or []
            if pre:
                pre[0] = f"Close {gaps[0]} with one focused weekly deliverable before the opportunity window starts."

        if strengths:
            highlights = out.get("insight_highlights") or []
            if highlights:
                highlights[0] = f"Leverage your strength in {strengths[0]} to improve execution quality in priority windows."

        if any("no relocation" in item for item in constraints):
            def _clean_relocation(text: str) -> str:
                t = text.replace("relocation", "location-flexible options")
                t = t.replace("Relocation", "Location-flexible options")
                t = t.replace("relocate", "shift location")
                t = t.replace("Relocate", "Shift location")
                return t

            for row in out.get("career_intent_scores", []):
                row["next_step"] = _clean_relocation(str(row.get("next_step", "")))
            out["recommendation_summary"] = [_clean_relocation(str(x)) for x in (out.get("recommendation_summary") or [])]
            wg = out.get("window_guidance") or {}
            wg["opportunity_actions"] = [_clean_relocation(str(x)) for x in (wg.get("opportunity_actions") or [])]
            wg["caution_actions"] = [_clean_relocation(str(x)) for x in (wg.get("caution_actions") or [])]

        if isinstance(time_hours, int) and time_hours <= 3:
            ap = out.get("action_plan") or {}

            def _lighten(items: List[Any]) -> List[str]:
                out_items: List[str] = []
                for item in items:
                    text = str(item).strip().rstrip(".")
                    if not text:
                        out_items.append("Keep tasks short and focused this week")
                    else:
                        out_items.append(f"Keep this under 60 minutes: {text}.")
                return out_items

            ap["now_to_opportunity_start"] = _lighten(list(ap.get("now_to_opportunity_start") or []))
            ap["during_opportunity"] = _lighten(list(ap.get("during_opportunity") or []))
            ap["during_caution"] = _lighten(list(ap.get("during_caution") or []))

        assert_schema_and_values_unchanged(payload, out, self.allowlist_paths)
        return out

    def rewrite_insight(self, request_payload: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        req = AIRewriteRequest(request_payload=request_payload, user_profile=user_profile)
        baseline = self._get_baseline(req.request_payload)
        profile_payload = req.user_profile.model_dump(exclude_none=True) if req.user_profile is not None else None

        system_prompt = build_system_prompt(self.allowlist_paths)
        user_prompt = build_user_prompt(baseline, profile_payload)

        first_raw = self.llm_rewrite(system_prompt, user_prompt)
        try:
            first_json = self._parse_llm_json(first_raw)
            merged = self._merge_allowlisted_text(baseline, first_json)
            validated = self._validate_rewrite(baseline, merged)
            return self._apply_profile_guardrails(validated, profile_payload)
        except Exception as first_error:
            repair_prompt = build_repair_prompt(
                original_json=baseline,
                user_profile=profile_payload,
                bad_output=first_raw,
                violations=str(first_error),
                allowlist_paths=self.allowlist_paths,
            )
            second_raw = self.llm_rewrite(system_prompt, repair_prompt)
            second_json = self._parse_llm_json(second_raw)
            merged = self._merge_allowlisted_text(baseline, second_json)
            validated = self._validate_rewrite(baseline, merged)
            return self._apply_profile_guardrails(validated, profile_payload)
