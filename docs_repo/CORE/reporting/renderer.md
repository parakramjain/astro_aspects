# reporting.renderer

## Purpose
Core domain/business logic module.

## Public API
- `generate_report_pdf`
- `load_config_from_yaml`

## Internal Helpers
- `_sanitize_filename`

## Dependencies
- `__future__`
- `builders.appendix`
- `builders.cover`
- `builders.dashboard`
- `builders.key_moments`
- `builders.milestones`
- `builders.summary`
- `builders.timeline`
- `config`
- `datetime`
- `i18n`
- `json`
- `layout`
- `logging`
- `normalize`
- `pathlib`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`
- `yaml`

## Risks / TODOs
- `generate_report_pdf`: risky (Risk: broad exception catch; large function >80 LOC)

## Example Usage
```python
from reporting.renderer import generate_report_pdf
result = generate_report_pdf(...)
```
