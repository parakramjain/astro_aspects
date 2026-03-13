# spend_intel_engine.scoring.spend_profile_scorer

## Purpose
Core domain/business logic module.

## Public API
- `score_spend_profile`

## Internal Helpers
- `_angular_bonus`
- `_build_aspect_count`
- `_category_from_score`
- `_chart_hash_from_planets`
- `_compute_structure_signals`
- `_get_attr`
- `_house_sign_by_number`
- `_planet_map`
- `_prominence_score`
- `_ruler_stability_score`
- `_venus_condition_score`

## Dependencies
- `__future__`
- `collections`
- `hashlib`
- `json`
- `spend_intel_engine.domain.enums`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.utils.aspect_normalizer`
- `spend_intel_engine.utils.cache`
- `spend_intel_engine.utils.numbers`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.scoring.spend_profile_scorer import score_spend_profile
result = score_spend_profile(...)
```
