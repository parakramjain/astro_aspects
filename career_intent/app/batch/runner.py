from __future__ import annotations

import argparse
import csv
import datetime as dt
import traceback
from pathlib import Path
from typing import Dict, List

from career_intent.app.core.orchestrator import CareerIntentOrchestrator
from career_intent.app.schemas.input import BirthPayloadIn, CareerInsightRequest, TimeframeIn, SUPPORTED_INTENTS
from career_intent.app.utils.io import ensure_dir, safe_slug, write_json, write_text
from career_intent.app.utils.logging import get_logger, log_event


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _required_columns() -> List[str]:
    return [
        "name",
        "dateOfBirth",
        "timeOfBirth",
        "placeOfBirth",
        "timeZone",
        "latitude",
        "longitude",
        "lang_code",
        "career_intent",
    ]


def _validate_columns(rows: List[Dict[str, str]]) -> None:
    if not rows:
        raise ValueError("CSV has no data rows")
    keys = set(rows[0].keys())
    missing = [col for col in _required_columns() if col not in keys]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")


def _parse_date_optional(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Career intent batch runner")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--format", choices=["html", "pdf"], default="html")
    args = parser.parse_args(argv)

    logger = get_logger("career_intent.batch")
    orchestrator = CareerIntentOrchestrator()

    csv_path = Path(args.csv)
    outdir = Path(args.outdir)
    ensure_dir(outdir)

    rows = _read_csv(csv_path)
    _validate_columns(rows)

    success = 0
    fallback = 0
    failed = 0
    failures: List[Dict[str, str]] = []

    for idx, row in enumerate(rows, start=1):
        try:
            birth = BirthPayloadIn(
                name=row.get("name", ""),
                dateOfBirth=row.get("dateOfBirth", ""),
                timeOfBirth=row.get("timeOfBirth", ""),
                placeOfBirth=row.get("placeOfBirth", ""),
                timeZone=row.get("timeZone", ""),
                latitude=float(row.get("latitude", 0.0)),
                longitude=float(row.get("longitude", 0.0)),
                lang_code=row.get("lang_code", "en") or "en",
            )
            timeframe = TimeframeIn(
                months=int(row.get("months") or args.months),
                start_date=_parse_date_optional(row.get("start_date") or None),
                end_date=_parse_date_optional(row.get("end_date") or None),
            )
            intent_raw = row.get("career_intent", "Skill Building")
            intent_value = intent_raw if intent_raw in SUPPORTED_INTENTS else "Skill Building"
            req = CareerInsightRequest.model_validate(
                {
                    "birth_payload": birth.model_dump(),
                    "career_intent": intent_value,
                    "timeframe": timeframe.model_dump(),
                }
            )
            request_id = f"batch-{idx:05d}"
            insight = orchestrator.generate(req, request_id=request_id)

            stem = f"{safe_slug(birth.name)}_{safe_slug(birth.dateOfBirth)}"
            json_path = outdir / f"{stem}_career_insight.json"
            write_json(json_path, insight)

            if args.format == "pdf":
                pdf_bytes = orchestrator.render_pdf(insight)
                if pdf_bytes:
                    (outdir / f"{stem}_career_report.pdf").write_bytes(pdf_bytes)
                else:
                    html = orchestrator.render_html(insight)
                    write_text(outdir / f"{stem}_career_report.html", html)
            else:
                html = orchestrator.render_html(insight)
                write_text(outdir / f"{stem}_career_report.html", html)

            if insight.get("metadata", {}).get("fallback_flags"):
                fallback += 1
            success += 1
            log_event(logger, "batch_record_processed", index=idx, request_id=request_id, name=birth.name)
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "row_index": str(idx),
                    "name": row.get("name", ""),
                    "error": str(exc),
                    "trace": traceback.format_exc(limit=1).strip(),
                }
            )

    if failures:
        failure_path = outdir / "failures.csv"
        with failure_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["row_index", "name", "error", "trace"])
            writer.writeheader()
            writer.writerows(failures)

    log_event(logger, "batch_summary", success=success, fallback=fallback, failed=failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
