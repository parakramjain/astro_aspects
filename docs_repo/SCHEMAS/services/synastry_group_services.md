# services.synastry_group_services

## Purpose
Schemas/models module defining data contracts.

## Public API
- `PersonInput.cache_key`
- `PersonInput.validate_timezone`
- `analyze_group`
- `analyze_group_api_payload`
- `clamp_0_100`
- `compute_pair`
- `describe_pair`
- `explain_pair_kpis`
- `get_natal`
- `is_supported_type`
- `kpi_catalog`
- `rank_top`
- `register_custom_kpi`
- `safe_mean`
- `scale_0_100`
- `short_summary_builder`
- `to_shareable_card`
- `weights_profile`
- `z_score_to_0_100`

## Internal Helpers
- `_aggregate_group_kpis`
- `_badge_for_score`
- `_cohesion_metrics`
- `_compose_total_group_score`
- `_detect_outliers_cliques`
- `_ensure_project_root_on_syspath`
- `_normalize_weights`
- `_pair_kpi_scores`
- `_pair_total_score`
- `_person_to_natal_payload`
- `_to_person_input`

## Dependencies
- `__future__`
- `astro_core.astro_core`
- `dataclasses`
- `functools`
- `itertools`
- `json`
- `logging`
- `math`
- `networkx`
- `numpy`
- `os`
- `pydantic`
- `schemas`
- `services.synastry_services`
- `services.synastry_vedic_services`
- `statistics`
- `sys`
- `typing`
- `zoneinfo`

## Risks / TODOs
- `PersonInput.validate_timezone`: risky (Risk: broad exception catch)
- `clamp_0_100`: risky (Risk: broad exception catch)
- `scale_0_100`: risky (Risk: broad exception catch)
- `z_score_to_0_100`: risky (Risk: broad exception catch)
- `get_natal`: risky (Risk: broad exception catch)
- `_pair_kpi_scores`: risky (Risk: broad exception catch)
- `_cohesion_metrics`: risky (Risk: broad exception catch)
- `_detect_outliers_cliques`: risky (Risk: broad exception catch)
- `analyze_group`: risky (Risk: broad exception catch)
- `_to_person_input`: risky (Risk: broad exception catch)

## Example Usage
```python
from services.synastry_group_services import PersonInput
obj = PersonInput(...)
result = obj.cache_key(...)
```
