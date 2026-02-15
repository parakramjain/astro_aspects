# Reporting (PDF)

This package converts the JSON output produced by `automation/batch_report_runner.py` into a polished PDF using **ReportLab Platypus**.

## Required fonts

Place these TTF files in `reporting/fonts/` (or set the corresponding `*_path` fields in `ReportConfig`):

- `NotoSansDevanagari-Regular.ttf`
- `NotoSansDevanagari-Bold.ttf`
- `NotoSans-Regular.ttf`
- `NotoSans-Bold.ttf`

If the fonts are missing, the renderer raises a clear `FileNotFoundError`.

## Programmatic usage

```python
from pathlib import Path
import json

from reporting.config import ReportConfig
from reporting.renderer import generate_report_pdf

json_data = json.loads(Path("output/sample.json").read_text(encoding="utf-8"))
config = ReportConfig(report_type="DAILY", language_mode="HI", output_dir=Path("out"))
pdf_path = generate_report_pdf(json_data, config)
print(pdf_path)
```

## CLI usage

```bash
python -m reporting.cli --input output\\Amit__1982-08-16__1D__2026-01-16.json --report-type DAILY --language HI --out out
```
