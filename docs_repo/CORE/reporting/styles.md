# reporting.styles

## Purpose
Core domain/business logic module.

## Public API
- `build_styles`
- `register_fonts`

## Internal Helpers
- `_resolve_font_path`

## Dependencies
- `__future__`
- `config`
- `dataclasses`
- `logging`
- `pathlib`
- `reportlab.lib`
- `reportlab.lib.enums`
- `reportlab.lib.styles`
- `reportlab.pdfbase`
- `reportlab.pdfbase.ttfonts`
- `typing`

## Risks / TODOs
- `build_styles`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from reporting.styles import build_styles
result = build_styles(...)
```
