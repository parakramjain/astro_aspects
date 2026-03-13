# reporting.normalize

## Purpose
Core domain/business logic module.

## Public API
- `aspect_is_challenging`
- `aspect_is_positive`
- `bilingual_text`
- `derive_executive_fields`
- `fmt_date`
- `fmt_dt`
- `format_date_hi`
- `get_lang_text`
- `normalize_life_event_description`
- `parse_iso_date`
- `parse_iso_datetime`
- `pick_keywords`
- `safe_parse_stringified_dict`
- `smart_no_orphan_last_word`
- `to_local`

## Internal Helpers
- `_coerce_to_str_list`

## Dependencies
- `__future__`
- `ast`
- `config`
- `dataclasses`
- `datetime`
- `logging`
- `pytz`
- `typing`

## Risks / TODOs
- `parse_iso_datetime`: risky (Risk: broad exception catch; silent exception handling)
- `safe_parse_stringified_dict`: risky (Risk: broad exception catch)

## Example Usage
```python
from reporting.normalize import aspect_is_challenging
result = aspect_is_challenging(...)
```
