# reporting.tests.test_report_compact

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_compact_page_count_daily_smoke`
- `test_cover_title_single_occurrence`
- `test_datetime_formatting_local`
- `test_i18n_titles_language_mode`
- `test_skip_empty_timeline_items`

## Internal Helpers
- `_extract_text`
- `_fonts_present`
- `_sample_json`

## Dependencies
- `__future__`
- `pathlib`
- `pypdf`
- `pytest`
- `reporting.config`
- `reporting.i18n`
- `reporting.renderer`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.tests.test_report_compact import test_compact_page_count_daily_smoke
result = test_compact_page_count_daily_smoke(...)
```
