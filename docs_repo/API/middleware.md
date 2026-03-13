# middleware

## Purpose
API layer module exposing request handlers and routing.

## Public API
- `LoggingMiddleware.dispatch`
- `RequestIDMiddleware.dispatch`

## Internal Helpers
- `LoggingMiddleware.__init__`
- `RequestIDMiddleware.__init__`

## Dependencies
- `__future__`
- `fastapi`
- `starlette.middleware.base`
- `time`
- `typing`
- `uuid`

## Risks / TODOs
- `LoggingMiddleware.dispatch`: risky (Risk: broad exception catch)

## Example Usage
```python
from middleware import LoggingMiddleware
obj = LoggingMiddleware(...)
result = obj.dispatch(...)
```
