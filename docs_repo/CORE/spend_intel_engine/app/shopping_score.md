# spend_intel_engine.app.shopping_score

## Purpose
Core domain/business logic module.

## Public API
- `main`

## Internal Helpers
- `_parser`

## Dependencies
- `__future__`
- `argparse`
- `dataclasses`
- `datetime`
- `json`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.shopping_engine`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.app.shopping_score import main
result = main(...)
```
