from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from spend_intel_engine.exporters.shopping_insights_csv_exporter import (
    DailyScore,
    Driver,
    InsightsMetrics,
    ShoppingInsights,
    SpendProfile,
    export_shopping_insights_to_csv,
)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sample_insights() -> ShoppingInsights:
    return ShoppingInsights(
        run_id="run-123",
        ruleset_version="rules-v1",
        spend_profile=SpendProfile(
            score=77,
            category="Spender",
            description="Sample description",
            top_drivers=[
                Driver(code="D1", weight=1.2, implication="Imp 1", matched_aspect="VEN TRI JUP"),
                Driver(code="D2", weight=-0.4, implication="Imp 2", matched_aspect=None),
            ],
        ),
        daily_scores=[
            DailyScore(
                date=date(2026, 3, 2),
                score=105,
                confidence=0.756,
                note="Day note",
                top_drivers=[
                    Driver(code="T1", weight=2.1, implication="DayImp1", matched_aspect="MOO CON VEN"),
                ],
            )
        ],
        metrics=InsightsMetrics(
            ruleset_version="rules-v1",
            n_days=1,
            daily_score_mean=63.25,
            daily_score_std=4.5,
            positive_event_count=2,
            negative_event_count=1,
            mapped_aspect_ratio=0.5,
            fallback_rate=0.25,
            top_driver_frequencies={"VEN TRI JUP": 2, "MOO CON VEN": 1},
        ),
    )


def test_file_naming(tmp_path: Path) -> None:
    insights = _sample_insights()
    out = export_shopping_insights_to_csv(insights, tmp_path, prefix="batchA")

    assert out["spend_profile"].name == "batchA__spend_profile.csv"
    assert out["daily_scores"].name == "batchA__daily_scores.csv"
    assert out["metrics"].name == "batchA__metrics.csv"


def test_driver_padding(tmp_path: Path) -> None:
    insights = _sample_insights()
    out = export_shopping_insights_to_csv(insights, tmp_path)

    spend_rows = _read_csv_rows(out["spend_profile"])
    assert len(spend_rows) == 1
    spend = spend_rows[0]
    assert spend["top_driver_5_code"] == ""
    assert float(spend["top_driver_5_weight"]) == 0.0

    daily_rows = _read_csv_rows(out["daily_scores"])
    assert len(daily_rows) == 1
    daily = daily_rows[0]
    assert daily["top_driver_3_code"] == ""
    assert float(daily["top_driver_3_weight"]) == 0.0


def test_date_formatting_and_score_clamp(tmp_path: Path) -> None:
    insights = _sample_insights()
    out = export_shopping_insights_to_csv(insights, tmp_path)

    daily_rows = _read_csv_rows(out["daily_scores"])
    daily = daily_rows[0]

    assert daily["date"] == "2026-03-02"
    assert daily["score"] == "100"  # clamped from 105
    assert daily["confidence"] == "0.76"


def test_metrics_json_serialization(tmp_path: Path) -> None:
    insights = _sample_insights()
    out = export_shopping_insights_to_csv(insights, tmp_path)

    metrics_rows = _read_csv_rows(out["metrics"])
    assert len(metrics_rows) == 1
    metrics = metrics_rows[0]

    parsed = json.loads(metrics["top_driver_frequencies_json"])
    assert parsed == {"MOO CON VEN": 1, "VEN TRI JUP": 2}
