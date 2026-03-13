# utils.email_formatting_utils

## Purpose
Shared utility/helper module.

## Public API
- `render_basic_forecast_html_daily`
- `render_basic_forecast_html_weekly`
- `safe_extract_forecast_dict`

## Internal Helpers
- `_as_list_str`
- `_render_bullets`

## Dependencies
- `__future__`
- `dataclasses`
- `html`
- `json`
- `typing`
- External integration tags: email

## Risks / TODOs
- `render_basic_forecast_html_daily`: risky (Risk: hardcoded URL; large function >80 LOC)
- `render_basic_forecast_html_weekly`: risky (Risk: hardcoded URL; large function >80 LOC)

## Example Usage
```python
from utils.email_formatting_utils import render_basic_forecast_html_daily
result = render_basic_forecast_html_daily(...)
```
