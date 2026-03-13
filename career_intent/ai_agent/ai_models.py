from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel

from career_intent.app.schemas.user_profile import UserProfileContext


class AIRewriteRequest(BaseModel):
    request_payload: Dict[str, Any]
    user_profile: Optional[UserProfileContext] = None
