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
from utils.email_formatting_utils import render_basic_forecast_html_daily, render_basic_forecast_html_weekly
from services.report_services import dailyWeeklyTimeline

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


def run_batch(csv_path: Path, output_dir: Path, send_email_ind: bool = False) -> List[BatchRowResult]:
    rows = read_natal_csv(csv_path)
    validate_required_columns(rows)

    output_dir.mkdir(parents=True, exist_ok=True)

    results: List[BatchRowResult] = []
    for idx, row in enumerate(rows[2:], start=1):
        try:
            req = build_timeline_request(row)
            lang_code = row.get("lang_code", "en")
            print(f"Processing Weekly Prediction for: {req.name}...")
            # update req.reportStartDate to current date for weekly report
            req = req.model_copy(update={"reportStartDate": datetime.now().strftime("%Y-%m-%d")})
            # update req.timePeriod to "1W" for weekly report
            req = req.model_copy(update={"timePeriod": "1W"})
            print(f"Input: {req}")
            output = dailyWeeklyTimeline(req, day_or_week="weekly", lang_code=lang_code)

            stem = "__".join(
                [
                    _safe_filename(req.name),
                    _safe_filename(req.dateOfBirth),
                    _safe_filename(req.timePeriod),
                    _safe_filename(req.reportStartDate),
                ]
            )
            # write output.shortSummary to text file for now, can be changed to PDF or JSON later
            out_path = output_dir / f"{stem}.txt"
            out_path.write_text(output.shortSummary, encoding="utf-8")

            # Email send logic for each recepient.

            to_email = row.get("email")
            name = row.get("name", "there")
            if send_email_ind and to_email and output:
                try:
                    try:
                        html_body = render_basic_forecast_html_weekly(output.shortSummary)
                    except Exception:
                        html_body = f"<p>{output.shortSummary.replace(chr(10), '<br>')}</p><br><p>Best regards,<br>Astro Consultant Team</p>"
                    send_email(
                        to_email=to_email,
                        subject=f"{name} Your Weekly Astro Timeline Report.",
                        body=f"{output.shortSummary}\n\nBest regards,\nAstro Consultant Team",
                        html_body=html_body,
                        pdf_path='',
                    )
                    print(f"Email sent to {to_email}")
                except Exception as exc:
                    print(f"Failed to send email to {to_email}: {exc}")
                    continue

            results.append(BatchRowResult(row_index=idx, input=row, output_path=None, ok=True))
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
            "timePeriod": "1W",
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
    python -m automation.batch_report_runner_weekly --csv ./automation/sample_natal_inputs.csv --output ./output
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
        help="Write automation/natal_inputs_for_weekly_forecast.csv and run it to ./output",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send emails with the generated reports",
    )

    args = parser.parse_args(argv)

    if args.demo:
        sample_csv = Path(__file__).with_name("natal_inputs_for_weekly_forecast.csv")
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
    python -m automation.batch_report_runner_weekly --csv ./automation/natal_inputs_for_weekly_forecast.csv --output ./output --send-email
    """
    raise SystemExit(main())
