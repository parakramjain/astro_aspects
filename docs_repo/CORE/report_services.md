# report_services

## Purpose
Core domain/business logic module.

## Public API
- `compute_life_events`
- `compute_timeline`
- `dailyWeeklyTimeline`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `aspect_card_utils.aspect_card_mgmt`
- `astro_core.astro_core`
- `datetime`
- `schemas`
- `typing`

## Risks / TODOs
- `compute_life_events`: risky (Risk: broad exception catch; large function >80 LOC)
- `compute_timeline`: risky (Risk: broad exception catch; large function >80 LOC; silent exception handling)

## Example Usage
```python
from report_services import compute_life_events
result = compute_life_events(...)
```
