# spend_intel_engine.tests.test_purchase_type

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_base_amplitude_constants`
- `test_get_purchase_advice`
- `test_has_outer_planet_hard_aspect`
- `test_impulsive_luxury_guardrail`
- `test_metrics_data_returned`
- `test_purchase_type_affects_scoring`
- `test_purchase_type_enum`
- `test_risk_multiplier_constants`
- `test_thrifty_essentials_boost`

## Internal Helpers
- `MockLifeEvent.__init__`

## Dependencies
- `__future__`
- `datetime`
- `pytest`
- `spend_intel_engine.domain.enums`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.scoring.daily_scorer`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.tests.test_purchase_type import test_base_amplitude_constants
result = test_base_amplitude_constants(...)
```
