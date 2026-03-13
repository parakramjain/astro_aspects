# utils.timeline_report_pdf

## Purpose
Shared utility/helper module.

## Public API
- `create_timeline_pdf_report`

## Internal Helpers
- `_format_ai_summary`
- `_get_cinzel_font_name`
- `_get_devanagari_font_name`
- `_resolve_output_path`
- `_resolve_plot_image`

## Dependencies
- `__future__`
- `json`
- `os`
- `pathlib`
- `reportlab.lib.enums`
- `reportlab.lib.pagesizes`
- `reportlab.lib.styles`
- `reportlab.pdfbase`
- `reportlab.pdfbase.ttfonts`
- `reportlab.platypus`
- `schemas`
- `tempfile`
- `typing`
- `xml.sax.saxutils`

## Risks / TODOs
- `_get_devanagari_font_name`: risky (Risk: broad exception catch)
- `_get_cinzel_font_name`: risky (Risk: broad exception catch)
- `_format_ai_summary`: risky (Risk: broad exception catch)
- `create_timeline_pdf_report`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from utils.timeline_report_pdf import create_timeline_pdf_report
result = create_timeline_pdf_report(...)
```
