from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from reporting.config import ReportConfig
from reporting.renderer import generate_report_pdf

def generate_pdf_from_batch_output(
    json_path: Path,
    *,
    report_type: Literal["DAILY", "WEEKLY"] = "DAILY",
    language_mode: Literal["HI", "EN", "BILINGUAL"] = "EN",
    output_dir: Optional[Path] = None,
    file_name: Optional[str] = None,
) -> Path:
    """Convenience wrapper used by other scripts.

    Input is the JSON file produced by `automation/batch_report_runner.py`.
    """

    data = json.loads(json_path.read_text(encoding="utf-8"))

    cfg = ReportConfig(report_type=report_type, language_mode=language_mode)
    if output_dir is not None:
        cfg.output_dir = output_dir
    if file_name is not None:
        cfg.override_file_name = file_name

    return generate_report_pdf(data, cfg)

if __name__ == "__main__":
    """
    Sample command to execute this code directly from command line:
    python -m utils.report_generator ./output/Amit__1982-08-16__1Y__2026-01-01.json --out ./out --report-type DAILY --language EN --file-name "Amit__1982-08-16__1Y__2026-01-01.pdf"
    """
    
    import argparse

    parser = argparse.ArgumentParser(description="Generate astrology PDF report from JSON file.")
    parser.add_argument("json_path", type=Path, help="Path to report JSON (from batch_report_runner)")
    parser.add_argument("--out", type=Path, default=None, help="Output directory (overrides config.output_dir)")
    parser.add_argument(
        "--report-type",
        choices=["DAILY", "WEEKLY"],
        default="DAILY",
        help="Type of report to generate",
    )
    parser.add_argument(
        "--language",
        choices=["HI", "EN", "BILINGUAL"],
        default="EN",
        help="Language mode for the report",
    )
    parser.add_argument(
        "--file-name",
        type=str,
        default=None,
        help="Optional explicit output file name (overrides naming template)",
    )

    args = parser.parse_args()

    out_path = generate_pdf_from_batch_output(
        args.json_path,
        report_type=args.report_type,
        language_mode=args.language,
        output_dir=args.out,
        file_name=args.file_name,
    )
    print(f"Generated report at: {out_path}")