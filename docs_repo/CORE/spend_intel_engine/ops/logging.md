# spend_intel_engine.ops.logging

## Purpose
Core domain/business logic module.

## Public API
- `log_shopping_run`
- `log_structured`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `json`
- `logging`
- `typing`

## Risks / TODOs
- `log_shopping_run`: needs refactor (Refactor: excessive parameters)

## Example Usage
```python
from spend_intel_engine.ops.logging import log_shopping_run
result = log_shopping_run(...)
```
