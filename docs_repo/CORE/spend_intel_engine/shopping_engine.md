# spend_intel_engine.shopping_engine

## Purpose
Core domain/business logic module.

## Public API
- `compute_shopping_insights`

## Internal Helpers
- `_as_schema_payload`
- `_logger`

## Dependencies
- `__future__`
- `dataclasses`
- `datetime`
- `exporters.shopping_insights_csv_exporter`
- `logging`
- `pathlib`
- `schemas`
- `services.natal_services`
- `services.report_services`
- `spend_intel_engine.domain.models`
- `spend_intel_engine.ops.logging`
- `spend_intel_engine.ops.metrics`
- `spend_intel_engine.rules.loader`
- `spend_intel_engine.scoring.daily_scorer`
- `spend_intel_engine.scoring.spend_profile_scorer`
- `spend_intel_engine.utils.cache`
- `sys`
- `typing`
- `uuid`

## Risks / TODOs
- `compute_shopping_insights`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from spend_intel_engine.shopping_engine import compute_shopping_insights
result = compute_shopping_insights(...)
```
