# spend_intel_engine.tests.test_ops

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_compute_metrics_empty`
- `test_compute_metrics_fallback_rate`
- `test_compute_metrics_top_drivers`
- `test_compute_metrics_with_data`
- `test_detect_ruleset_shift_both`
- `test_detect_ruleset_shift_mean`
- `test_detect_ruleset_shift_std`

## Internal Helpers
- `MockLifeEvent.__init__`

## Dependencies
- `__future__`
- `datetime`
- `pytest`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.ops.drift`
- `spend_intel_engine.ops.metrics`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.tests.test_ops import test_compute_metrics_empty
result = test_compute_metrics_empty(...)
```
