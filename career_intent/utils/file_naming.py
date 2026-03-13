from __future__ import annotations

import re
from pathlib import Path


def sanitize_name_for_file(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "user"
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return cleaned.lower() or "user"


def build_report_file_paths(user_name: str | None, output_dir: str | Path = "output/career_intent_output") -> tuple[str, str]:
    out_dir = Path(output_dir)
    base_name = f"{sanitize_name_for_file(user_name)}_career_progression_report"
    html_path = out_dir / f"{base_name}.html"
    pdf_path = out_dir / f"{base_name}.pdf"
    return str(html_path), str(pdf_path)
