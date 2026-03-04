from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


LOGGER = logging.getLogger("shopping_insights_csv_exporter")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


def _log_structured(event: str, **kwargs: Any) -> None:
    payload = {"event": event, **kwargs}
    LOGGER.info(json.dumps(payload, default=str))


@dataclass(frozen=True)
class Driver:
    code: str
    weight: float
    implication: str
    matched_aspect: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Driver":
        return cls(
            code=str(data.get("code", "")),
            weight=float(data.get("weight", 0.0) or 0.0),
            implication=str(data.get("implication", "")),
            matched_aspect=(str(data.get("matched_aspect")) if data.get("matched_aspect") is not None else None),
        )


@dataclass(frozen=True)
class SpendProfile:
    score: int
    category: str
    description: str
    top_drivers: List[Driver] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpendProfile":
        drivers = [Driver.from_dict(item) for item in list(data.get("top_drivers", []) or [])]
        return cls(
            score=int(data.get("score", 0) or 0),
            category=str(data.get("category", "")),
            description=str(data.get("description", "")),
            top_drivers=drivers,
        )


@dataclass(frozen=True)
class DailyScore:
    date: date
    score: int
    confidence: float
    top_drivers: List[Driver] = field(default_factory=list)
    note: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DailyScore":
        raw_date = data.get("date", "")
        parsed_date = date.fromisoformat(str(raw_date))
        drivers = [Driver.from_dict(item) for item in list(data.get("top_drivers", []) or [])]
        return cls(
            date=parsed_date,
            score=int(data.get("score", 0) or 0),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            top_drivers=drivers,
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True)
class InsightsMetrics:
    ruleset_version: str
    n_days: int
    daily_score_mean: float
    daily_score_std: float
    positive_event_count: int
    negative_event_count: int
    mapped_aspect_ratio: float
    fallback_rate: float
    top_driver_frequencies: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InsightsMetrics":
        return cls(
            ruleset_version=str(data.get("ruleset_version", "")),
            n_days=int(data.get("n_days", 0) or 0),
            daily_score_mean=float(data.get("daily_score_mean", 0.0) or 0.0),
            daily_score_std=float(data.get("daily_score_std", 0.0) or 0.0),
            positive_event_count=int(data.get("positive_event_count", 0) or 0),
            negative_event_count=int(data.get("negative_event_count", 0) or 0),
            mapped_aspect_ratio=float(data.get("mapped_aspect_ratio", 0.0) or 0.0),
            fallback_rate=float(data.get("fallback_rate", 0.0) or 0.0),
            top_driver_frequencies=dict(data.get("top_driver_frequencies", {}) or {}),
        )


@dataclass(frozen=True)
class ShoppingInsights:
    spend_profile: SpendProfile
    daily_scores: List[DailyScore]
    ruleset_version: str
    run_id: str
    metrics: Optional[InsightsMetrics] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShoppingInsights":
        spend_profile = SpendProfile.from_dict(dict(data.get("spend_profile", {}) or {}))
        daily_scores = [DailyScore.from_dict(item) for item in list(data.get("daily_scores", []) or [])]

        metrics_raw = data.get("metrics", None)
        metrics = InsightsMetrics.from_dict(dict(metrics_raw)) if isinstance(metrics_raw, Mapping) else None

        return cls(
            spend_profile=spend_profile,
            daily_scores=daily_scores,
            ruleset_version=str(data.get("ruleset_version", "")),
            run_id=str(data.get("run_id", "")),
            metrics=metrics,
        )


def _get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_driver(obj: Any) -> Driver:
    if isinstance(obj, Driver):
        return obj
    if isinstance(obj, Mapping):
        return Driver.from_dict(obj)
    return Driver(
        code=str(_get_attr_or_key(obj, "code", "")),
        weight=float(_get_attr_or_key(obj, "weight", 0.0) or 0.0),
        implication=str(_get_attr_or_key(obj, "implication", "")),
        matched_aspect=(
            str(_get_attr_or_key(obj, "matched_aspect")) if _get_attr_or_key(obj, "matched_aspect") is not None else None
        ),
    )


def _to_spend_profile(obj: Any) -> SpendProfile:
    if isinstance(obj, SpendProfile):
        return obj
    if isinstance(obj, Mapping):
        return SpendProfile.from_dict(obj)
    top_drivers = [_to_driver(item) for item in list(_get_attr_or_key(obj, "top_drivers", []) or [])]
    return SpendProfile(
        score=int(_get_attr_or_key(obj, "score", 0) or 0),
        category=str(_get_attr_or_key(obj, "category", "")),
        description=str(_get_attr_or_key(obj, "description", "")),
        top_drivers=top_drivers,
    )


def _to_daily_score(obj: Any) -> DailyScore:
    if isinstance(obj, DailyScore):
        return obj
    if isinstance(obj, Mapping):
        return DailyScore.from_dict(obj)

    raw_date = _get_attr_or_key(obj, "date", None)
    if isinstance(raw_date, date):
        parsed_date = raw_date
    else:
        parsed_date = date.fromisoformat(str(raw_date))

    top_drivers = [_to_driver(item) for item in list(_get_attr_or_key(obj, "top_drivers", []) or [])]

    return DailyScore(
        date=parsed_date,
        score=int(_get_attr_or_key(obj, "score", 0) or 0),
        confidence=float(_get_attr_or_key(obj, "confidence", 0.0) or 0.0),
        top_drivers=top_drivers,
        note=str(_get_attr_or_key(obj, "note", "")),
    )


def _to_metrics(obj: Any, ruleset_version: str = "") -> Optional[InsightsMetrics]:
    if obj is None:
        return None
    if isinstance(obj, InsightsMetrics):
        return obj
    if isinstance(obj, Mapping):
        data = dict(obj)
        if not data.get("ruleset_version"):
            data["ruleset_version"] = ruleset_version
        return InsightsMetrics.from_dict(data)

    return InsightsMetrics(
        ruleset_version=str(_get_attr_or_key(obj, "ruleset_version", ruleset_version) or ruleset_version),
        n_days=int(_get_attr_or_key(obj, "n_days", 0) or 0),
        daily_score_mean=float(_get_attr_or_key(obj, "daily_score_mean", 0.0) or 0.0),
        daily_score_std=float(_get_attr_or_key(obj, "daily_score_std", 0.0) or 0.0),
        positive_event_count=int(_get_attr_or_key(obj, "positive_event_count", 0) or 0),
        negative_event_count=int(_get_attr_or_key(obj, "negative_event_count", 0) or 0),
        mapped_aspect_ratio=float(_get_attr_or_key(obj, "mapped_aspect_ratio", 0.0) or 0.0),
        fallback_rate=float(_get_attr_or_key(obj, "fallback_rate", 0.0) or 0.0),
        top_driver_frequencies=dict(_get_attr_or_key(obj, "top_driver_frequencies", {}) or {}),
    )


def _to_shopping_insights(insights: Any) -> ShoppingInsights:
    if isinstance(insights, ShoppingInsights):
        return insights
    if isinstance(insights, Mapping):
        return ShoppingInsights.from_dict(insights)

    ruleset_version = str(_get_attr_or_key(insights, "ruleset_version", ""))
    run_id = str(_get_attr_or_key(insights, "run_id", ""))
    spend_profile = _to_spend_profile(_get_attr_or_key(insights, "spend_profile", {}))
    daily_scores = [_to_daily_score(item) for item in list(_get_attr_or_key(insights, "daily_scores", []) or [])]
    metrics = _to_metrics(_get_attr_or_key(insights, "metrics", None), ruleset_version=ruleset_version)

    return ShoppingInsights(
        spend_profile=spend_profile,
        daily_scores=daily_scores,
        ruleset_version=ruleset_version,
        run_id=run_id,
        metrics=metrics,
    )


def _driver_cells(drivers: List[Driver], slots: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    norm = list(drivers[:slots])
    while len(norm) < slots:
        norm.append(Driver(code="", weight=0.0, implication="", matched_aspect=""))

    for index, item in enumerate(norm, start=1):
        out[f"top_driver_{index}_code"] = item.code
        out[f"top_driver_{index}_weight"] = float(item.weight)
        out[f"top_driver_{index}_implication"] = item.implication
        out[f"top_driver_{index}_matched_aspect"] = item.matched_aspect or ""
    return out


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _write_csv(path: Path, columns: List[str], rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_shopping_insights_to_csv(
    insights: Any,
    output_dir: Path,
    prefix: str | None = None,
    export_drivers: bool = False,
) -> Dict[str, Path]:
    normalized = _to_shopping_insights(insights)

    output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = prefix or normalized.run_id

    _log_structured(
        "export_start",
        run_id=normalized.run_id,
        ruleset_version=normalized.ruleset_version,
        output_dir=str(output_dir),
        prefix=file_prefix,
        export_drivers=export_drivers,
    )

    spend_profile_path = output_dir / f"{file_prefix}__spend_profile.csv"
    daily_scores_path = output_dir / f"{file_prefix}__daily_scores.csv"
    metrics_path = output_dir / f"{file_prefix}__metrics.csv"

    spend_profile_columns: List[str] = [
        "run_id",
        "ruleset_version",
        "spend_score",
        "spend_category",
        "spend_description",
    ]
    for rank in range(1, 6):
        spend_profile_columns.extend(
            [
                f"top_driver_{rank}_code",
                f"top_driver_{rank}_weight",
                f"top_driver_{rank}_implication",
                f"top_driver_{rank}_matched_aspect",
            ]
        )

    spend_row = {
        "run_id": normalized.run_id,
        "ruleset_version": normalized.ruleset_version,
        "spend_score": _clamp_score(normalized.spend_profile.score),
        "spend_category": normalized.spend_profile.category,
        "spend_description": normalized.spend_profile.description,
        **_driver_cells(normalized.spend_profile.top_drivers, slots=5),
    }
    _write_csv(spend_profile_path, spend_profile_columns, [spend_row])

    daily_columns: List[str] = ["run_id", "ruleset_version", "date", "score", "confidence", "note"]
    for rank in range(1, 4):
        daily_columns.extend(
            [
                f"top_driver_{rank}_code",
                f"top_driver_{rank}_weight",
                f"top_driver_{rank}_implication",
                f"top_driver_{rank}_matched_aspect",
            ]
        )

    daily_rows: List[Dict[str, Any]] = []
    for day in normalized.daily_scores:
        daily_rows.append(
            {
                "run_id": normalized.run_id,
                "ruleset_version": normalized.ruleset_version,
                "date": day.date.isoformat(),
                "score": _clamp_score(day.score),
                "confidence": f"{float(day.confidence):.2f}",
                "note": day.note,
                **_driver_cells(day.top_drivers, slots=3),
            }
        )
    _write_csv(daily_scores_path, daily_columns, daily_rows)

    metrics = normalized.metrics or InsightsMetrics(
        ruleset_version=normalized.ruleset_version,
        n_days=len(normalized.daily_scores),
        daily_score_mean=0.0,
        daily_score_std=0.0,
        positive_event_count=0,
        negative_event_count=0,
        mapped_aspect_ratio=0.0,
        fallback_rate=0.0,
        top_driver_frequencies={},
    )

    metrics_columns = [
        "run_id",
        "ruleset_version",
        "n_days",
        "daily_score_mean",
        "daily_score_std",
        "positive_event_count",
        "negative_event_count",
        "mapped_aspect_ratio",
        "fallback_rate",
        "top_driver_frequencies_json",
    ]
    metrics_row = {
        "run_id": normalized.run_id,
        "ruleset_version": metrics.ruleset_version or normalized.ruleset_version,
        "n_days": int(metrics.n_days),
        "daily_score_mean": float(metrics.daily_score_mean),
        "daily_score_std": float(metrics.daily_score_std),
        "positive_event_count": int(metrics.positive_event_count),
        "negative_event_count": int(metrics.negative_event_count),
        "mapped_aspect_ratio": float(metrics.mapped_aspect_ratio),
        "fallback_rate": float(metrics.fallback_rate),
        "top_driver_frequencies_json": json.dumps(metrics.top_driver_frequencies, ensure_ascii=False, sort_keys=True),
    }
    _write_csv(metrics_path, metrics_columns, [metrics_row])

    export_paths: Dict[str, Path] = {
        "spend_profile": spend_profile_path,
        "daily_scores": daily_scores_path,
        "metrics": metrics_path,
    }

    drivers_rows: List[Dict[str, Any]] = []
    if export_drivers:
        drivers_path = output_dir / f"{file_prefix}__drivers_long.csv"
        drivers_columns = [
            "run_id",
            "ruleset_version",
            "entity_type",
            "date",
            "driver_rank",
            "code",
            "weight",
            "implication",
            "matched_aspect",
        ]

        for rank, driver in enumerate(normalized.spend_profile.top_drivers, start=1):
            drivers_rows.append(
                {
                    "run_id": normalized.run_id,
                    "ruleset_version": normalized.ruleset_version,
                    "entity_type": "spend_profile",
                    "date": "",
                    "driver_rank": rank,
                    "code": driver.code,
                    "weight": float(driver.weight),
                    "implication": driver.implication,
                    "matched_aspect": driver.matched_aspect or "",
                }
            )

        for day in normalized.daily_scores:
            for rank, driver in enumerate(day.top_drivers, start=1):
                drivers_rows.append(
                    {
                        "run_id": normalized.run_id,
                        "ruleset_version": normalized.ruleset_version,
                        "entity_type": "daily_score",
                        "date": day.date.isoformat(),
                        "driver_rank": rank,
                        "code": driver.code,
                        "weight": float(driver.weight),
                        "implication": driver.implication,
                        "matched_aspect": driver.matched_aspect or "",
                    }
                )

        _write_csv(drivers_path, drivers_columns, drivers_rows)
        export_paths["drivers_long"] = drivers_path

    _log_structured(
        "export_done",
        run_id=normalized.run_id,
        spend_profile_path=str(spend_profile_path),
        daily_scores_path=str(daily_scores_path),
        metrics_path=str(metrics_path),
        spend_profile_rows=1,
        daily_scores_rows=len(daily_rows),
        metrics_rows=1,
        drivers_long_rows=len(drivers_rows) if export_drivers else 0,
    )

    return export_paths


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export ShoppingInsights JSON to CSV files")
    parser.add_argument("--input-json", required=True, dest="input_json", help="Path to serialized ShoppingInsights JSON")
    parser.add_argument("--out", required=True, dest="out_dir", help="Output directory for CSV files")
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--export-drivers", action="store_true", dest="export_drivers")
    args = parser.parse_args(argv)

    input_path = Path(args.input_json)
    out_dir = Path(args.out_dir)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    insights = ShoppingInsights.from_dict(payload)
    paths = export_shopping_insights_to_csv(
        insights=insights,
        output_dir=out_dir,
        prefix=args.prefix,
        export_drivers=args.export_drivers,
    )

    print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
