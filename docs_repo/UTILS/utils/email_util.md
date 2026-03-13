# utils.email_util

## Purpose
Shared utility/helper module.

## Public API
- `send_email`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `dotenv`
- `email`
- `email.message`
- `email.mime.base`
- `email.mime.multipart`
- `email.mime.text`
- `html`
- `os`
- `smtplib`
- External integration tags: email

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from utils.email_util import send_email
result = send_email(...)
```
