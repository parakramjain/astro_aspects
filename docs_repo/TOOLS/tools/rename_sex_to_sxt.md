# tools.rename_sex_to_sxt

## Purpose
Tools/automation/testing/CLI module.

## Public API
- `find_root`
- `main`
- `rewrite_aspect_file`
- `update_index_json`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `argparse`
- `json`
- `os`
- `sys`
- `typing`

## Risks / TODOs
- `rewrite_aspect_file`: risky (Risk: broad exception catch)
- `update_index_json`: risky (Risk: broad exception catch; silent exception handling)
- `main`: risky (Risk: broad exception catch)

## Example Usage
```python
from tools.rename_sex_to_sxt import find_root
result = find_root(...)
```
