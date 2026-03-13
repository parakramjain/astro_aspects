# spend_intel_engine.exporters.shopping_insights_csv_exporter

## Purpose
Core domain/business logic module.

## Public API
- `DailyScore.from_dict`
- `Driver.from_dict`
- `InsightsMetrics.from_dict`
- `ShoppingInsights.from_dict`
- `SpendProfile.from_dict`
- `export_shopping_insights_to_csv`

## Internal Helpers
- `_clamp_score`
- `_cli`
- `_driver_cells`
- `_get_attr_or_key`
- `_log_structured`
- `_to_daily_score`
- `_to_driver`
- `_to_metrics`
- `_to_shopping_insights`
- `_to_spend_profile`
- `_write_csv`

## Dependencies
- `__future__`
- `argparse`
- `csv`
- `dataclasses`
- `datetime`
- `json`
- `logging`
- `pathlib`
- `typing`

## Risks / TODOs
- `export_shopping_insights_to_csv`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from spend_intel_engine.exporters.shopping_insights_csv_exporter import DailyScore
obj = DailyScore(...)
result = obj.from_dict(...)
```
