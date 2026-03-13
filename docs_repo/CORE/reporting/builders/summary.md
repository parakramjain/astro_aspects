# reporting.builders.summary

## Purpose
Core domain/business logic module.

## Public API
- `build_summary_story`

## Internal Helpers
- `_action_from_item`
- `_best_time_from_items`
- `_first_with_nature`
- `_headline_from_item`
- `_nature_weight`
- `_rank_timeline_items`
- `_truncate`

## Dependencies
- `__future__`
- `components`
- `config`
- `datetime`
- `i18n`
- `normalize`
- `pytz`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.builders.summary import build_summary_story
result = build_summary_story(...)
```
