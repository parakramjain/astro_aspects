from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .config import ReportConfig
from .renderer import generate_report_pdf, load_config_from_yaml


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate astrology PDF report from JSON.")
    parser.add_argument("--input", type=Path, required=True, help="Path to report JSON (from batch_report_runner)")
    parser.add_argument("--out", type=Path, default=None, help="Output directory (overrides config.output_dir)")
    parser.add_argument("--config", type=Path, default=None, help="Optional YAML config file")
    parser.add_argument("--report-type", choices=["DAILY", "WEEKLY"], default="DAILY")
    parser.add_argument("--language", choices=["HI", "EN", "BILINGUAL"], default="HI")

    args = parser.parse_args(argv)

    if args.config:
        cfg = load_config_from_yaml(args.config)
    else:
        cfg = ReportConfig(report_type=args.report_type, language_mode=args.language)

    if args.out is not None:
        cfg.output_dir = args.out

    data = json.loads(args.input.read_text(encoding="utf-8"))
    out_path = generate_report_pdf(data, cfg)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
