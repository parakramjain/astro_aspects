# reporting.tests.test_normalize

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_date_normalization`
- `test_language_fallback_hi_to_en`
- `test_life_event_description_dict_passthrough`
- `test_life_event_description_plain_string`
- `test_life_event_description_stringified_dict`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `reporting.normalize`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.tests.test_normalize import test_date_normalization
result = test_date_normalization(...)
```
