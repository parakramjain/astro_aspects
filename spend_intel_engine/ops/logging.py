"""Structured logging utilities."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict


def log_structured(
    logger: logging.LoggerAdapter,
    level: str,
    message: str,
    **kwargs: Any,
) -> None:
    """Log structured JSON data.
    
    Args:
        logger: Logger adapter with context
        level: Log level (info, warning, error)
        message: Human-readable message
        **kwargs: Additional structured fields
    """
    log_data = {
        "message": message,
        **kwargs,
    }
    
    log_line = json.dumps(log_data, default=str)
    
    if level == "info":
        logger.info(log_line)
    elif level == "warning":
        logger.warning(log_line)
    elif level == "error":
        logger.error(log_line)
    else:
        logger.debug(log_line)


def log_shopping_run(
    logger: logging.LoggerAdapter,
    run_id: str,
    user_hash: str,
    ruleset_version: str,
    purchase_type: str,
    spend_profile_category: str,
    fallback_rate: float,
    n_days: int,
    mean_score: float,
) -> None:
    """Log shopping insights run with structured data.
    
    Does NOT log any raw PII.
    """
    log_structured(
        logger,
        "info",
        "shopping_insights_complete",
        run_id=run_id,
        user_hash=user_hash,
        ruleset_version=ruleset_version,
        purchase_type=purchase_type,
        spend_profile_category=spend_profile_category,
        fallback_rate=fallback_rate,
        n_days=n_days,
        mean_score=mean_score,
    )
