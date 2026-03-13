# aspect_card_utils.aspect_report

## Purpose
Core domain/business logic module.

## Public API
- `canonicalize_order`
- `generate_report_from_rows`
- `load_card`
- `load_index`
- `normalize_aspect_tuple`
- `parse_aspect_rows`
- `phase_for_today`
- `render_item_md`
- `resolve_card_id`

## Internal Helpers
- `_parse_date`

## Dependencies
- `__future__`
- `dataclasses`
- `datetime`
- `json`
- `os`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from aspect_card_utils.aspect_report import canonicalize_order
result = canonicalize_order(...)
```
