# spend_intel_engine.rules.loader

## Purpose
Core domain/business logic module.

## Public API
- `load_rule_maps`

## Internal Helpers
- `_load_rule_maps_cached`
- `_read_csv_map`
- `_read_csv_map_cached`
- `_resolve_csv_path`
- `_ruleset_hash`

## Dependencies
- `__future__`
- `functools`
- `hashlib`
- `pandas`
- `pathlib`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.utils.aspect_normalizer`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.rules.loader import load_rule_maps
result = load_rule_maps(...)
```
