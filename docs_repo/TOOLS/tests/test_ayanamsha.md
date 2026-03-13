# tests.test_ayanamsha

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `TestAyanamsha.test_sidereal_vs_tropical`
- `TestAyanamsha.test_user_custom_offset`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `astro_core.astro_core`
- `datetime`
- `pathlib`
- `swisseph`
- `sys`
- `unittest`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from tests.test_ayanamsha import TestAyanamsha
obj = TestAyanamsha(...)
result = obj.test_sidereal_vs_tropical(...)
```
