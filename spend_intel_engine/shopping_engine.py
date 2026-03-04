from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any

# Make root-level modules importable when running this file directly:
# python .\spend_intel_engine\shopping_engine.py
_ROOT_DIR = Path(__file__).resolve().parents[1]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from schemas import BirthPayload as SchemaBirthPayload
from services.natal_services import calculate_natal_chart_data, compute_natal_natal_aspects
from services.report_services import compute_life_events
from spend_intel_engine.domain.models import BirthPayload, ScoringContext, ShoppingCfg, ShoppingInsights
from spend_intel_engine.ops.logging import log_shopping_run
from spend_intel_engine.ops.metrics import compute_metrics
from spend_intel_engine.rules.loader import load_rule_maps
from spend_intel_engine.scoring.daily_scorer import score_daily_shopping
from spend_intel_engine.scoring.spend_profile_scorer import score_spend_profile
from spend_intel_engine.utils.cache import compute_user_hash


def _as_schema_payload(payload: BirthPayload) -> SchemaBirthPayload:
    return SchemaBirthPayload(**asdict(payload))


def _logger(cfg: ShoppingCfg, run_id: str) -> logging.LoggerAdapter:
    logger = logging.getLogger(cfg.logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logging.LoggerAdapter(logger, extra={"run_id": run_id})


def compute_shopping_insights(
    payload: BirthPayload,
    start_date: date,
    n_days: int,
    cfg: ShoppingCfg,
    purchase_type: str = "big_ticket",
) -> ShoppingInsights:
    run_id = str(uuid.uuid4())
    ctx = ScoringContext(run_id=run_id, metadata={"n_days": n_days, "start_date": start_date.isoformat()})
    logger = _logger(cfg, run_id)

    effective_cfg = cfg if cfg.purchase_type == purchase_type else replace(cfg, purchase_type=purchase_type)

    logger.info("shopping_insights_start run_id=%s name=%s", ctx.run_id, payload.name)
    schema_payload = _as_schema_payload(payload)

    # Compute user hash for anonymized logging
    user_hash = compute_user_hash(payload.dateOfBirth, payload.timeOfBirth, payload.placeOfBirth)

    natal_chart = calculate_natal_chart_data(schema_payload)
    natal_aspects = compute_natal_natal_aspects(schema_payload)
    life_events = compute_life_events(schema_payload, start_date=start_date, horizon_days=n_days)

    rules = load_rule_maps(effective_cfg)

    spend_profile = score_spend_profile(
        natal_chart_data=natal_chart,
        natal_aspects=natal_aspects,
        rule_maps=rules,
        cfg=effective_cfg,
    )

    # Updated to receive metrics_data
    daily_scores, metrics_data = score_daily_shopping(
        life_events=life_events,
        start_date=start_date,
        n_days=n_days,
        profile=spend_profile,
        rule_maps=rules,
        cfg=effective_cfg,
        return_metrics=True,
    )

    # Compute comprehensive metrics
    metrics = compute_metrics(
        daily_scores=daily_scores,
        life_events=metrics_data.get("life_events", []),
        mapped_count=metrics_data.get("mapped_events", 0),
        total_events=metrics_data.get("total_events", 0),
        fallback_count=metrics_data.get("fallback_events", 0),
        ruleset_version=rules.ruleset_version,
    )

    # Structured logging
    log_shopping_run(
        logger=logger,
        run_id=ctx.run_id,
        user_hash=user_hash,
        ruleset_version=rules.ruleset_version,
        purchase_type=effective_cfg.purchase_type,
        spend_profile_category=spend_profile.category,
        fallback_rate=metrics.fallback_rate,
        n_days=len(daily_scores),
        mean_score=metrics.daily_score_mean,
    )

    logger.info(
        "shopping_insights_done run_id=%s profile_score=%s days=%s ruleset=%s",
        ctx.run_id,
        spend_profile.score,
        len(daily_scores),
        rules.ruleset_version,
    )

    return ShoppingInsights(
        spend_profile=spend_profile,
        daily_scores=daily_scores,
        ruleset_version=rules.ruleset_version,
        run_id=ctx.run_id,
        metrics=metrics,
    )

# write unit tests for compute_shopping_insights in a separate test file, mocking external dependencies and verifying the structure of the returned ShoppingInsights object.
if __name__ == "__main__":
    # Example usage
    payload = BirthPayload(
        name="John Doe",
        dateOfBirth=date(1983, 3, 28).isoformat(),
        timeOfBirth="12:00",
        placeOfBirth="Indore India",
        timeZone="Asia/Kolkata",
        latitude=22.7196,
        longitude=75.8577,
    )
    insights = compute_shopping_insights(
        payload=payload,
        start_date=date(2026, 1, 1),
        n_days=30,
        cfg=ShoppingCfg(),
        purchase_type="essentials",
    )
    # use module exporters.shopping_insights_csv_exporter to export insights to csv
    from exporters.shopping_insights_csv_exporter import export_shopping_insights_to_csv
    export_shopping_insights_to_csv(insights, Path("./output/spend/"), prefix="example_run")
    print(f"Processing complete. Insights exported to CSV at ./output/spend/ with prefix 'example_run'.")
