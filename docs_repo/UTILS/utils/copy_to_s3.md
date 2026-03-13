# utils.copy_to_s3

## Purpose
Shared utility/helper module.

## Public API
- `upload_file_to_s3`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `boto3`
- `botocore.exceptions`
- `dataclasses`
- `dotenv`
- `os`
- `typing`
- External integration tags: aws

## Risks / TODOs
- `upload_file_to_s3`: risky (Risk: possible hardcoded secret/token)

## Example Usage
```python
from utils.copy_to_s3 import upload_file_to_s3
result = upload_file_to_s3(...)
```
