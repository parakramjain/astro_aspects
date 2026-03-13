# reporting.builders.timeline

## Purpose
Core domain/business logic module.

## Public API
- `build_timeline_story`

## Internal Helpers
- `_action_bullets`
- `_action_first`
- `_badge_for_nature`
- `_facet_bullets`
- `_facet_tags`
- `_is_empty_item`
- `_timeline_card`
- `_timeline_card_compact`
- `_truncate`
- `_truncate_short`

## Dependencies
- `__future__`
- `components`
- `config`
- `datetime`
- `i18n`
- `logging`
- `normalize`
- `pytz`
- `reportlab.lib.units`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`

## Risks / TODOs
- `_timeline_card`: risky (Risk: large function >80 LOC)
- `build_timeline_story`: risky (Risk: broad exception catch)

## Example Usage
```python
from reporting.builders.timeline import build_timeline_story
result = build_timeline_story(...)
```
