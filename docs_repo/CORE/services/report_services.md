# services.report_services

## Purpose
Core domain/business logic module.

## Public API
- `compute_daily_weekly_ai_summary`
- `compute_life_events`
- `compute_report_ai_summary`
- `compute_timeline`
- `dailyWeeklyTimeline`
- `generate_report_pdf`
- `upcoming_event`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `aspect_card_utils.aspect_card_mgmt`
- `ast`
- `astro_core.astro_core`
- `datetime`
- `pytz`
- `schemas`
- `services.ai_agent_services`
- `services.ai_prompt_service`
- `typing`
- `utils.copy_to_s3`
- `utils.email_util`
- `utils.text_utils`
- `utils.timeline_report_pdf`
- `utils.timeline_report_plot`
- `utils.timeline_report_text`
- External integration tags: email

## Risks / TODOs
- `compute_life_events`: risky (Risk: broad exception catch; large function >80 LOC)
- `compute_timeline`: risky (Risk: broad exception catch; large function >80 LOC; silent exception handling)
- `upcoming_event`: risky (Risk: broad exception catch; large function >80 LOC)

## Example Usage
```python
from services.report_services import compute_daily_weekly_ai_summary
result = compute_daily_weekly_ai_summary(...)
```
