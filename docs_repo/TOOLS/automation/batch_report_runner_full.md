# automation.batch_report_runner_full

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `build_timeline_request`
- `generate_report_for_row`
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
- `typing`
- `utils.email_util`
- External integration tags: email

## Risks / TODOs
- `run_batch`: risky (Risk: broad exception catch)

## Example Usage
```python
from automation.batch_report_runner_full import build_timeline_request
result = build_timeline_request(...)
```
