# spend_intel_engine.tests.test_shopping_insights_csv_exporter

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `test_date_formatting_and_score_clamp`
- `test_driver_padding`
- `test_file_naming`
- `test_metrics_json_serialization`

## Internal Helpers
- `_read_csv_rows`
- `_sample_insights`

## Dependencies
- `__future__`
- `csv`
- `datetime`
- `json`
- `pathlib`
- `spend_intel_engine.exporters.shopping_insights_csv_exporter`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from spend_intel_engine.tests.test_shopping_insights_csv_exporter import test_date_formatting_and_score_clamp
result = test_date_formatting_and_score_clamp(...)
```
