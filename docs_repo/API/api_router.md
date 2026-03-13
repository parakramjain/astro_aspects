# api_router

## Purpose
API layer module exposing request handlers and routing.

## Public API
- `build_natal_chart`
- `compat_ashtakoota`
- `compat_group`
- `compat_pair`
- `daily_weekly`
- `dignities_table`
- `life_events`
- `natal_aspects`
- `natal_characteristics`
- `report_timeline`
- `soulmate_finder`
- `upcoming_events`

## Internal Helpers
- `_ensure_dict_from_ai_summary`
- `_require_api_headers`

## Dependencies
- `__future__`
- `astro_core.astro_core`
- `dataclasses`
- `datetime`
- `fastapi`
- `json`
- `schemas`
- `services.natal_services`
- `services.report_services`
- `services.synastry_group_services`
- `services.synastry_services`
- `services.synastry_vedic_services`
- `typing`
- `uuid`

## Risks / TODOs
- `report_timeline`: risky (Risk: broad exception catch)
- `daily_weekly`: risky (Risk: broad exception catch)
- `compat_group`: risky (Risk: broad exception catch)

## Example Usage
```python
from api_router import build_natal_chart
result = build_natal_chart(...)
```

## Endpoints
- `POST /natal/build-chart` handled by `api_router:build_natal_chart`
- `POST /natal/dignities-table` handled by `api_router:dignities_table`
- `POST /natal/aspects` handled by `api_router:natal_aspects`
- `POST /natal/characteristics` handled by `api_router:natal_characteristics`
- `POST /reports/life-events` handled by `api_router:life_events`
- `POST /reports/timeline` handled by `api_router:report_timeline`
- `POST /reports/daily-weekly` handled by `api_router:daily_weekly`
- `POST /reports/upcoming-events` handled by `api_router:upcoming_events`
- `POST /compat/synastry` handled by `api_router:compat_pair`
- `POST /compat/group` handled by `api_router:compat_group`
- `POST /compat/soulmate-finder` handled by `api_router:soulmate_finder`
- `POST /compat/ashtakoota` handled by `api_router:compat_ashtakoota`
