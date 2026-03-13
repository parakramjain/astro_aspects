# reporting.builders.key_moments

## Purpose
Core domain/business logic module.

## Public API
- `build_key_moments_story`

## Internal Helpers
- `_advice_from_keypoints`

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
from reporting.builders.key_moments import build_key_moments_story
result = build_key_moments_story(...)
```
