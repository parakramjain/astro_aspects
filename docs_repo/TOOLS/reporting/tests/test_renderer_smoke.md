# reporting.tests.test_renderer_smoke

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_generate_pdf_smoke`

## Internal Helpers
- `_fonts_present`

## Dependencies
- `__future__`
- `json`
- `pathlib`
- `pytest`
- `reporting.config`
- `reporting.renderer`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.tests.test_renderer_smoke import test_generate_pdf_smoke
result = test_generate_pdf_smoke(...)
```
