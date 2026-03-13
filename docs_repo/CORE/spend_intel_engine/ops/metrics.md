# spend_intel_engine.ops.metrics

## Purpose
Core domain/business logic module.

## Public API
- `compute_metrics`

## Internal Helpers
- `_is_positive_event`

## Dependencies
- `__future__`
- `collections`
- `numpy`
- `spend_intel_engine.domain.models`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.ops.metrics import compute_metrics
result = compute_metrics(...)
```
