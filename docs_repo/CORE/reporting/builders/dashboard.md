# reporting.builders.dashboard

## Purpose
Core domain/business logic module.

## Public API
- `build_dashboard_story`

## Internal Helpers
- `_area_bullets`
- `_has_text`
- `_score_by_area`
- `_truncate`

## Dependencies
- `__future__`
- `components`
- `config`
- `i18n`
- `normalize`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.builders.dashboard import build_dashboard_story
result = build_dashboard_story(...)
```
