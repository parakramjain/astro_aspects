# automation.batch_report_runner_daily

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `build_timeline_request`
- `main`
- `read_natal_csv`
- `run_batch`
- `validate_required_columns`
- `write_sample_csv`

## Internal Helpers
- `_normalize_row`
- `_parse_float`
- `_safe_filename`

## Dependencies
- `__future__`
- `argparse`
- `csv`
- `dataclasses`
- `datetime`
- `json`
- `pathlib`
- `schemas`
- `services`
- `services.report_services`
- `typing`
- `utils.email_formatting_utils`
- `utils.email_util`
- External integration tags: email

## Risks / TODOs
- `run_batch`: risky (Risk: broad exception catch)

## Example Usage
```python
from automation.batch_report_runner_daily import build_timeline_request
result = build_timeline_request(...)
```
