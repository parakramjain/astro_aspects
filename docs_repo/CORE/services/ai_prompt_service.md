# services.ai_prompt_service

## Purpose
Core domain/business logic module.

## Public API
- `get_system_prompt_daily`
- `get_system_prompt_natal`
- `get_system_prompt_qna`
- `get_system_prompt_report`
- `get_system_prompt_weekly`
- `get_user_prompt_daily`
- `get_user_prompt_daily_weekly_old`
- `get_user_prompt_natal`
- `get_user_prompt_qna`
- `get_user_prompt_report`
- `get_user_prompt_weekly`

## Internal Helpers
- `_normalize_lang_code`

## Dependencies
- `schemas`
- External integration tags: email

## Risks / TODOs
- `get_system_prompt_report`: risky (Risk: large function >80 LOC)
- `get_system_prompt_natal`: risky (Risk: large function >80 LOC)
- `get_system_prompt_weekly`: risky (Risk: large function >80 LOC)
- `get_user_prompt_daily`: risky (Risk: hardcoded URL)
- `get_user_prompt_weekly`: risky (Risk: hardcoded URL; large function >80 LOC)

## Example Usage
```python
from services.ai_prompt_service import get_system_prompt_daily
result = get_system_prompt_daily(...)
```
