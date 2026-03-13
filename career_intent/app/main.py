from __future__ import annotations

from fastapi import FastAPI

from career_intent.app.api.routes import router
from career_intent.app.config.settings import get_settings

settings = get_settings()
app = FastAPI(title="Career Intent API", version=settings.app_version)
app.include_router(router)
