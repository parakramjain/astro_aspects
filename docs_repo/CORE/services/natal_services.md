# services.natal_services

## Purpose
Core domain/business logic module.

## Public API
- `calculate_natal_chart_data`
- `compute_natal_ai_summary`
- `compute_natal_natal_aspects`
- `format_lon_as_sign`
- `lon_to_sign_deg_min`
- `planet_positions_and_houses`

## Internal Helpers
- `_as_12_cusps`
- `_asc_mc_and_cusps_utc`
- `_house_by_cusps`
- `_house_whole_sign`
- `_houses_compat`
- `_julday_utc`
- `_norm360`
- `_normalize_deg`
- `_planet_longitudes_utc`
- `_sign_index`
- `_to_utc`
- `_wrap_cusp_segment`

## Dependencies
- `aspect_card_utils.aspect_card_mgmt`
- `astro_core.astro_core`
- `datetime`
- `schemas`
- `services.ai_agent_services`
- `services.ai_prompt_service`
- `swisseph`
- `typing`
- `zoneinfo`

## Risks / TODOs
- `planet_positions_and_houses`: risky (Risk: broad exception catch; large function >80 LOC)

## Example Usage
```python
from services.natal_services import calculate_natal_chart_data
result = calculate_natal_chart_data(...)
```
