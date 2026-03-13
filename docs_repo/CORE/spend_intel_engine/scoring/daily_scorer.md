# spend_intel_engine.scoring.daily_scorer

## Purpose
Core domain/business logic module.

## Public API
- `score_daily_shopping`

## Internal Helpers
- `_add_moon_phases`
- `_add_moon_triggers`
- `_amplitude`
- `_aspect_type`
- `_build_note`
- `_compute_daily_contributions_vectorized`
- `_event_weight`
- `_get_attr`
- `_get_purchase_advice`
- `_has_outer_planet_hard_aspect`
- `_numeric_proximity`
- `_polarity`
- `_preprocess_events`

## Dependencies
- `__future__`
- `collections`
- `datetime`
- `numpy`
- `pandas`
- `spend_intel_engine.domain.enums`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.utils.aspect_normalizer`
- `spend_intel_engine.utils.dates`
- `spend_intel_engine.utils.numbers`
- `typing`
- `warnings`

## Risks / TODOs
- `score_daily_shopping`: risky (Risk: large function >80 LOC)
- `_add_moon_triggers`: needs refactor (Refactor: excessive parameters)

## Example Usage
```python
from spend_intel_engine.scoring.daily_scorer import score_daily_shopping
result = score_daily_shopping(...)
```
