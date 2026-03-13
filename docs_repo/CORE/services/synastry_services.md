# services.synastry_services

## Purpose
Core domain/business logic module.

## Public API
- `calculate_compatibility_scores`
- `calculate_planetary_angles`
- `calculate_synastry`
- `get_natal_characteristics`

## Internal Helpers
- `_delta_circ`
- `_dist_to_aspect`
- `_elemental_balance_score`
- `_normalize_name`
- `_parse_person_input`
- `_score_aspect_list`
- `_short`
- `_sign_from_lon`

## Dependencies
- `__future__`
- `astro_core.astro_core`
- `json`
- `math`
- `os`
- `swisseph`
- `sys`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from services.synastry_services import calculate_compatibility_scores
result = calculate_compatibility_scores(...)
```
