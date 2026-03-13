# astro_core.astro_services

## Purpose
Core domain/business logic module.

## Public API
- `build_aspect_dict`

## Internal Helpers
- `_canon_planet`
- `_color_for`
- `_fmt`
- `_prediction_exclusions`

## Dependencies
- `astro_core.astro_core`
- `datetime`
- `pandas`
- `typing`

## Risks / TODOs
- `build_aspect_dict`: needs refactor (Refactor: excessive parameters)

## Example Usage
```python
from astro_core.astro_services import build_aspect_dict
result = build_aspect_dict(...)
```
