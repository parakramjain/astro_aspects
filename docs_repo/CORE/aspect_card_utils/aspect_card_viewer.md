# aspect_card_utils.aspect_card_viewer

## Purpose
Core domain/business logic module.

## Public API
- `render_card_readonly`
- `render_section_grid`

## Internal Helpers
- `_badge`
- `_collapsible`
- `_norm_actionables`
- `_norm_bilingual`
- `_norm_embedding_sections`
- `_norm_facet_block`
- `_render_list`

## Dependencies
- `__future__`
- `aspect_card_mgmt`
- `html`
- `typing`

## Risks / TODOs
- `render_card_readonly`: risky (Risk: large function >80 LOC)

## Example Usage
```python
from aspect_card_utils.aspect_card_viewer import render_card_readonly
result = render_card_readonly(...)
```
