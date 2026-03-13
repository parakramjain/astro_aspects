from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class CareerIntentSettings(BaseModel):

    app_name: str = "career_intent"
    app_version: str = "0.1.0"
    config_version: str = "1.0.0"
    registry_path: str = "docs_repo/FUNCTIONS/function_registry.csv"
    thresholds_path: str = "career_intent/config/thresholds.yaml"
    driver_map_path: str = "career_intent/config/driver_map.yaml"
    driver_catalog_path: str = "career_intent/config/driver_catalog.yaml"
    driver_taxonomy_path: str = "career_intent/config/driver_taxonomy.yaml"
    timezone_fallback: str = "UTC"

@lru_cache(maxsize=1)
def get_settings() -> CareerIntentSettings:
    return CareerIntentSettings(
        app_version=os.getenv("CAREER_INTENT_VERSION", "0.1.0"),
        config_version=os.getenv("CAREER_INTENT_CONFIG_VERSION", "1.0.0"),
    )


@lru_cache(maxsize=1)
def load_thresholds() -> Dict[str, Any]:
    settings = get_settings()
    path = Path(settings.thresholds_path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def load_driver_map() -> Dict[str, Any]:
    settings = get_settings()
    path = Path(settings.driver_map_path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def load_driver_catalog() -> Dict[str, Any]:
    settings = get_settings()
    path = Path(settings.driver_catalog_path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def load_driver_taxonomy() -> Dict[str, Any]:
    settings = get_settings()
    path = Path(settings.driver_taxonomy_path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
