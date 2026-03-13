# services.synastry_vedic_services

## Purpose
Core domain/business logic module.

## Public API
- `compute_ashtakoota_score`
- `derive_non_scoring_insights`
- `explain_ashtakoota`
- `get_moon_longitude`
- `interpret_total_score`
- `koota_compatibility_status`
- `moon_to_nakshatra_index_and_pada`
- `moon_to_rashi`
- `score_bhakoot`
- `score_gana`
- `score_graha_maitri`
- `score_nadi`
- `score_tara`
- `score_varna`
- `score_vashya`
- `score_yoni`
- `sum_scores`
- `to_datetime_local`
- `to_utc`
- `tropical_to_sidereal`
- `validate_input`

## Internal Helpers
- `_graha_relation`
- `_namecase_ayan`
- `_sign_distance`
- `_tara_group`

## Dependencies
- `__future__`
- `astro_core.astro_core`
- `dataclasses`
- `datetime`
- `os`
- `sys`
- `typing`
- `zoneinfo`

## Risks / TODOs
- `koota_compatibility_status`: risky (Risk: broad exception catch)
- `validate_input`: risky (Risk: broad exception catch)
- `to_datetime_local`: risky (Risk: broad exception catch)
- `to_utc`: risky (Risk: broad exception catch)
- `compute_ashtakoota_score`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from services.synastry_vedic_services import compute_ashtakoota_score
result = compute_ashtakoota_score(...)
```
