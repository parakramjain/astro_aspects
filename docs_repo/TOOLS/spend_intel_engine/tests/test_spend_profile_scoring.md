# spend_intel_engine.tests.test_spend_profile_scoring

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_score_clamping_and_category_mapping_high_risk`
- `test_score_clamping_low_end`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `spend_intel_engine.domain.models`
- `spend_intel_engine.scoring.spend_profile_scorer`
- `spend_intel_engine.tests.test_fixtures`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.tests.test_spend_profile_scoring import test_score_clamping_and_category_mapping_high_risk
result = test_score_clamping_and_category_mapping_high_risk(...)
```
