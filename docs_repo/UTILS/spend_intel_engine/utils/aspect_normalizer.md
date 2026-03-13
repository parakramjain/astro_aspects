# spend_intel_engine.utils.aspect_normalizer

## Purpose
Shared utility/helper module.

## Public API
- `normalize_aspect_code`
- `symmetric_keys`

## Internal Helpers
- `_canon_aspect`
- `_canon_planet`

## Dependencies
- `__future__`
- `re`
- `typing`

## Risks / TODOs
- `_canon_planet`: risky (Risk: possible hardcoded secret/token)
- `_canon_aspect`: risky (Risk: possible hardcoded secret/token)
- `normalize_aspect_code`: risky (Risk: possible hardcoded secret/token)

## Example Usage
```python
from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code
result = normalize_aspect_code(...)
```
