# services.ai_agent_services

## Purpose
Core domain/business logic module.

## Public API
- `calculate_token_cost`
- `calculate_total_cost`
- `generate_astrology_AI_summary`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `dotenv`
- `openai`
- `os`
- `services.ai_prompt_service`
- `typing`
- External integration tags: ai

## Risks / TODOs
- `calculate_token_cost`: risky (Risk: possible hardcoded secret/token)
- `calculate_total_cost`: risky (Risk: possible hardcoded secret/token)
- `generate_astrology_AI_summary`: risky (Risk: broad exception catch; possible hardcoded secret/token)

## Example Usage
```python
from services.ai_agent_services import calculate_token_cost
result = calculate_token_cost(...)
```
