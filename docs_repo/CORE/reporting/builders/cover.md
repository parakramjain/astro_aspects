# reporting.builders.cover

## Purpose
Core domain/business logic module.

## Public API
- `build_cover_story`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `config`
- `i18n`
- `layout`
- `normalize`
- `reportlab.lib.units`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.builders.cover import build_cover_story
result = build_cover_story(...)
```
