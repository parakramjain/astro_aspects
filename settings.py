from __future__ import annotations
import os
from typing import List


APP_NAME = os.getenv("APP_NAME", "Astro Vision — Core REST")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() in {"1","true","yes","on"}

CORS_ALLOW_ORIGINS: List[str] = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
TRUSTED_HOSTS: List[str] = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "*").split(",") if h.strip()]
GZIP_MIN_SIZE = int(os.getenv("GZIP_MIN_SIZE", "1000"))
REQUEST_LOGGING = os.getenv("REQUEST_LOGGING", "basic").lower()  # "off" | "basic" | "full"
