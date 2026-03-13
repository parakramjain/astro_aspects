# astro_core.astro_core

## Purpose
Core domain/business logic module.

## Public API
- `calc_aspect_periods`
- `calc_planet_pos`
- `current_ayanamsha_info`
- `effective_orb`
- `find_aspects`
- `format_dt`
- `get_flags`
- `set_ayanamsha`

## Internal Helpers
- `_delta_circ`
- `_dist_to_aspect`
- `_julday_utc`
- `_parse_date`
- `_parse_time`
- `_planet_longitudes_utc`
- `_planet_name_short`
- `_refine_exact_time`
- `_resolve_sidm_const`
- `_selfcheck_ayanamsha`
- `_sep_deg_at_local_dt`
- `_to_utc`

## Dependencies
- `__future__`
- `dataclasses`
- `datetime`
- `swisseph`
- `typing`
- `zoneinfo`

## Risks / TODOs
- `calc_aspect_periods`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from astro_core.astro_core import calc_aspect_periods
result = calc_aspect_periods(...)
```
