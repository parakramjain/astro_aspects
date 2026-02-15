from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from schemas import TimelineRequest
from services import report_services as report_services
from utils.email_util import send_email


@dataclass(frozen=True)
class BatchRowResult:
    row_index: int
    input: Dict[str, Any]
    output_path: Optional[Path]
    ok: bool
    error: Optional[str] = None


REQUIRED_COLUMNS: Tuple[str, ...] = (
    "name",
    "dateOfBirth",
    "timeOfBirth",
    "placeOfBirth",
    "timeZone",
    "latitude",
    "longitude",
    "timePeriod",
    "reportStartDate",
)


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "report"


def _parse_float(value: Any) -> float:
    if value is None:
        raise ValueError("missing")
    s = str(value).strip()
    if not s:
        raise ValueError("missing")
    return float(s)


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def read_natal_csv(csv_path: Path) -> List[Dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        rows = [_normalize_row(r) for r in reader]
    return rows


def validate_required_columns(rows: Iterable[Dict[str, Any]]) -> None:
    for r in rows:
        missing = [c for c in REQUIRED_COLUMNS if c not in r]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")
        return
    raise ValueError("CSV has no data rows")


def build_timeline_request(row: Dict[str, Any]) -> TimelineRequest:
    payload: Dict[str, Any] = dict(row)
    payload["latitude"] = _parse_float(payload.get("latitude"))
    payload["longitude"] = _parse_float(payload.get("longitude"))
    payload["lang_code"] = row.get("lang_code", "en")
    return TimelineRequest(**payload)


def generate_report_for_row(req: TimelineRequest, lang_code: str = 'en') -> str:
    # timeline = report_services.compute_timeline(req)
    # daily_weekly = report_services.dailyWeeklyTimeline(req)

    # report: Dict[str, Any] = {
    #     "input": req.model_dump(),
    #     "generatedAt": datetime.now(timezone.utc).isoformat(),
    #     "timeline": timeline.model_dump(),
    #     "dailyWeekly": daily_weekly.model_dump(),
    # }

    # try:
    #     life_events = report_services.compute_life_events(req)
    #     report["lifeEvents"] = [ev.model_dump() for ev in life_events]
    # except Exception as exc:
    #     report["lifeEventsError"] = str(exc)
    report_path = ""
    report_path = report_services.generate_report_pdf(req, lang_code=lang_code)
    return report_path


def run_batch(csv_path: Path, output_dir: Path, send_email_ind: bool = False) -> List[BatchRowResult]:
    rows = read_natal_csv(csv_path)
    validate_required_columns(rows)

    output_dir.mkdir(parents=True, exist_ok=True)

    results: List[BatchRowResult] = []
    for idx, row in enumerate(rows, start=1):
        try:
            req = build_timeline_request(row)
            lang_code = row.get("lang_code", "en")
            print(f"Processing Prediction for: {req.name}...")
            report_path = generate_report_for_row(req, lang_code=lang_code)

            stem = "__".join(
                [
                    _safe_filename(req.name),
                    _safe_filename(req.dateOfBirth),
                    _safe_filename(req.timePeriod),
                    _safe_filename(req.reportStartDate),
                ]
            )
            out_path = output_dir / f"{stem}.json"
            out_path.write_text(json.dumps(report_path, ensure_ascii=False, indent=2), encoding="utf-8")

            # Email send logic for each recepient.

            to_email = row.get("email")
            name = row.get("name", "there")
            if send_email_ind and to_email and report_path:
                try:
                    send_email(
                        to_email=to_email,
                        subject=f"{name} Your Astro Timeline Report.",
                        body=f"Hi {name},\n\nYour Astro Timeline report has been generated. Please find the attached PDF.\n\nBest regards,\nAstro Aspects Team",
                        pdf_path=str(report_path),
                    )
                    print(f"Email sent to {to_email}")
                except Exception as exc:
                    print(f"Failed to send email to {to_email}: {exc}")
                    continue

            results.append(BatchRowResult(row_index=idx, input=row, output_path=out_path, ok=True))
        except Exception as exc:
            results.append(BatchRowResult(row_index=idx, input=row, output_path=None, ok=False, error=str(exc)))
        
    return results


def write_sample_csv(sample_csv_path: Path) -> None:
    sample_csv_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "name": "Amit",
            "dateOfBirth": "1982-08-16",
            "timeOfBirth": "16:00:00",
            "placeOfBirth": "Indore, India",
            "timeZone": "Asia/Kolkata",
            "latitude": "22.6",
            "longitude": "75.83",
            "timePeriod": "1Y",
            "reportStartDate": "2026-01-01",
        }
        # {
        #     "name": "Riya",
        #     "dateOfBirth": "1993-02-20",
        #     "timeOfBirth": "06:10:00",
        #     "placeOfBirth": "Delhi, India",
        #     "timeZone": "Asia/Kolkata",
        #     "latitude": "28.6139",
        #     "longitude": "77.2090",
        #     "timePeriod": "1W",
        #     "reportStartDate": "2026-01-16",
        # },
    ]

    with sample_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Docstring for main
    Sample command to execute this code directly from command line:
    python -m automation.batch_report_runner --csv ./automation/sample_natal_inputs.csv --output ./output
    :param argv: Description
    :type argv: Optional[List[str]]
    :return: Description
    :rtype: int
    """

    parser = argparse.ArgumentParser(description="Batch-generate reports from a CSV of natal details.")
    parser.add_argument("--csv", dest="csv_path", type=Path, help="Path to input CSV")
    parser.add_argument(
        "--output",
        dest="output_dir",
        type=Path,
        default=Path("output"),
        help="Directory to write report JSON files (default: ./output)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Write automation/sample_natal_inputs.csv and run it to ./output",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send emails with the generated reports",
    )

    args = parser.parse_args(argv)

    if args.demo:
        sample_csv = Path(__file__).with_name("sample_natal_inputs.csv")
        write_sample_csv(sample_csv)
        csv_path = sample_csv
    else:
        if args.csv_path is None:
            parser.error("--csv is required unless --demo is used")
        csv_path = args.csv_path

    results = run_batch(csv_path=csv_path, output_dir=args.output_dir, send_email_ind=args.send_email)

    ok = sum(1 for r in results if r.ok)
    bad = len(results) - ok

    print(f"Generated: {ok} report(s)")
    if bad:
        print(f"Failed: {bad} row(s)")
        for r in results:
            if not r.ok:
                print(f"- Row {r.row_index}: {r.error}")

    return 0 if bad == 0 else 2


if __name__ == "__main__":
    """
    Sample command to execute this code directly from command line:
    python -m automation.batch_report_runner --csv ./automation/sample_natal_inputs.csv --output ./output --send-email False
    """
    raise SystemExit(main())
