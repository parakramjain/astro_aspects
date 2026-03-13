# reporting.builders.milestones

## Purpose
Core domain/business logic module.

## Public API
- `build_milestones_story`

## Internal Helpers
- `_humanize_transit_window`

## Dependencies
- `__future__`
- `collections`
- `components`
- `config`
- `datetime`
- `i18n`
- `logging`
- `normalize`
- `reportlab.platypus`
- `schema`
- `styles`
- `typing`

## Risks / TODOs
- `build_milestones_story`: risky (Risk: broad exception catch; large function >80 LOC)

## Example Usage
```python
from reporting.builders.milestones import build_milestones_story
result = build_milestones_story(...)
```
