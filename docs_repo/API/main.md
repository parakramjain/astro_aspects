# main

## Purpose
API layer module exposing request handlers and routing.

## Public API
- `healthz`
- `landing`
- `lifespan`
- `on_any_error`
- `on_http_exception`
- `on_validation_error`
- `readyz`

## Internal Helpers
- `_custom_openapi`
- `_load_openapi_schema`

## Dependencies
- `__future__`
- `api_router`
- `contextlib`
- `datetime`
- `fastapi`
- `fastapi.exceptions`
- `fastapi.middleware.cors`
- `fastapi.middleware.gzip`
- `fastapi.openapi.utils`
- `functools`
- `middleware`
- `pathlib`
- `schemas`
- `settings`
- `starlette.exceptions`
- `starlette.middleware.trustedhost`
- `starlette.responses`
- `typing`
- `uvicorn`
- `yaml`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from main import healthz
result = healthz(...)
```

## Endpoints
- `GET /` handled by `main:landing`
- `GET /healthz` handled by `main:healthz`
- `GET /readyz` handled by `main:readyz`
