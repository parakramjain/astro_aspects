# tests.test_api_smoke

## Purpose
API layer module exposing request handlers and routing.

## Public API
- `test_natal_characteristics_smoke`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `fastapi.testclient`
- `json`
- `main`

## Risks / TODOs
- `test_natal_characteristics_smoke`: risky (Risk: possible hardcoded secret/token)

## Example Usage
```python
from tests.test_api_smoke import test_natal_characteristics_smoke
result = test_natal_characteristics_smoke(...)
```
