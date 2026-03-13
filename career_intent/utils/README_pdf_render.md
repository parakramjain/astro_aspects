# HTML to PDF Renderer Utility

This utility converts HTML strings into saved `.html` and `.pdf` files.

## Location

- `career_intent/utils/html_pdf_renderer.py`
- `career_intent/utils/file_naming.py`
- `career_intent/utils/render_models.py`

## Dependencies

Preferred engine:
- Playwright + Chromium (`playwright` package and browser install)

Optional fallback:
- WeasyPrint (only used when `enable_fallback=True`)

## Basic usage

```python
from career_intent.utils.html_pdf_renderer import HtmlToPdfRenderer

renderer = HtmlToPdfRenderer(enable_fallback=False)
result = renderer.html_to_pdf(
    html_content=html_text,
    output_pdf_path="output/career_intent_output/user_career_progression_report.pdf",
)
print(result.model_dump())
```

## File naming helper

```python
from career_intent.utils.file_naming import build_report_file_paths

html_path, pdf_path = build_report_file_paths("Amit")
```

This returns paths like:
- `output/career_intent_output/amit_career_progression_report.html`
- `output/career_intent_output/amit_career_progression_report.pdf`
