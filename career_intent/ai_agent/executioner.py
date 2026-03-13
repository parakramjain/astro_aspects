from __future__ import annotations

import os
import uuid
from typing import Any, Dict

from career_intent.ai_agent.ai_agent_service import CareerTimingAIAgent
from career_intent.app.core.orchestrator import CareerIntentOrchestrator
from career_intent.app.schemas.input import CareerInsightRequest
from career_intent.app.utils.logging import get_logger, log_event


class CareerTimingAIExecutioner:
    _REQ_ID_KEY = "__request_id"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("CAREER_INTENT_AI_MODEL", "gpt-4.1")
        self.orchestrator = CareerIntentOrchestrator()
        self.logger = get_logger("career_intent_ai_agent")
        self.agent = CareerTimingAIAgent(
            llm_rewrite=self._llm_rewrite,
            fetch_full_insight=self._fetch_full_insight,
        )

    def _llm_rewrite(self, system_prompt: str, user_prompt: str) -> str:
        from services.ai_agent_services import generate_astrology_AI_summary

        return str(
            generate_astrology_AI_summary(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.model,
            )
        )

    def _fetch_full_insight(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(request_payload)
        request_id = str(payload.pop(self._REQ_ID_KEY, "")).strip() or str(uuid.uuid4())
        req = CareerInsightRequest.model_validate(payload)
        return self.orchestrator.generate(req, request_id=request_id)

    def execute(self, req: CareerInsightRequest, *, request_id: str) -> Dict[str, Any]:
        payload = req.model_dump()
        payload[self._REQ_ID_KEY] = request_id
        profile = req.user_profile.model_dump(exclude_none=True) if req.user_profile is not None else None
        log_event(
            self.logger,
            "career_timing_ai_rewrite",
            request_id=request_id,
            profile_present=profile is not None,
            profile_field_count=len(profile or {}),
            profile_keys=sorted(list((profile or {}).keys())),
        )
        return self.agent.rewrite_insight(payload, user_profile=profile)
