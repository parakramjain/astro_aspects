# spend_intel_engine.tests.test_daily_scoring

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_date_range_scoring_peaks_at_exact_date`
- `test_symmetric_mapping_applies_for_transit_implication`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `datetime`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.scoring.daily_scorer`
- `spend_intel_engine.tests.test_fixtures`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.tests.test_daily_scoring import test_date_range_scoring_peaks_at_exact_date
result = test_date_range_scoring_peaks_at_exact_date(...)
```
