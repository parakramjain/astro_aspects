# utils.llm_utils

## Purpose
Shared utility/helper module.

## Public API
- `count_response_tokens`
- `count_tokens`
- `get_token_encoder`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `tiktoken`
- `typing`
- External integration tags: ai

## Risks / TODOs
- `get_token_encoder`: risky (Risk: possible hardcoded secret/token)
- `count_tokens`: risky (Risk: possible hardcoded secret/token)
- `count_response_tokens`: risky (Risk: possible hardcoded secret/token)

## Example Usage
```python
from utils.llm_utils import count_response_tokens
result = count_response_tokens(...)
```
