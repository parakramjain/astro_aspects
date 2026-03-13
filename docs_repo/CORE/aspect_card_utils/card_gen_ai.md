# aspect_card_utils.card_gen_ai

## Purpose
Core domain/business logic module.

## Public API
- `generate_aspect_card`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `datetime`
- `json`
- `openai`
- External integration tags: ai

## Risks / TODOs
- `generate_aspect_card`: risky (Risk: broad exception catch; large function >80 LOC)

## Example Usage
```python
from aspect_card_utils.card_gen_ai import generate_aspect_card
result = generate_aspect_card(...)
```
