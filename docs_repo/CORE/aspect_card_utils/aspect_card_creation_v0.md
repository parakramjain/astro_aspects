# aspect_card_utils.aspect_card_creation_v0

## Purpose
Core domain/business logic module.

## Public API
- `canonical_pair`
- `ensure_dirs`
- `generate_cards`
- `id_for`
- `main`
- `make_card`
- `to_code_planet`
- `write_cards`

## Internal Helpers
- `_life_events_for`
- `_load_life_event_mapping`

## Dependencies
- `__future__`
- `aspect_card_utils.vedic_kb`
- `csv`
- `dataclasses`
- `datetime`
- `json`
- `os`
- `sys`
- `typing`

## Risks / TODOs
- `_load_life_event_mapping`: risky (Risk: broad exception catch; possible hardcoded secret/token)
- `write_cards`: risky (Risk: possible hardcoded secret/token)

## Example Usage
```python
from aspect_card_utils.aspect_card_creation_v0 import canonical_pair
result = canonical_pair(...)
```
