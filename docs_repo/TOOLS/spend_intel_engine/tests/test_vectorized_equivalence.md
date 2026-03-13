# spend_intel_engine.tests.test_vectorized_equivalence

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_vectorized_scoring_matches_legacy_baseline`

## Internal Helpers
- `SampleLifeEvent.__init__`
- `_legacy_daily_scores`

## Dependencies
- `__future__`
- `datetime`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.scoring.daily_scorer`
- `spend_intel_engine.utils.aspect_normalizer`
- `spend_intel_engine.utils.dates`
- `spend_intel_engine.utils.numbers`
- `typing`

## Risks / TODOs
- `SampleLifeEvent.__init__`: needs refactor (Refactor: excessive parameters)

## Example Usage
```python
from spend_intel_engine.tests.test_vectorized_equivalence import test_vectorized_scoring_matches_legacy_baseline
result = test_vectorized_scoring_matches_legacy_baseline(...)
```
