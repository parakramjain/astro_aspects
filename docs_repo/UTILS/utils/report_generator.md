# utils.report_generator

## Purpose
Shared utility/helper module.

## Public API
- `generate_pdf_from_batch_output`

## Internal Helpers
- No internal helper functions detected.

## Dependencies
- `__future__`
- `argparse`
- `json`
- `pathlib`
- `reporting.config`
- `reporting.renderer`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from utils.report_generator import generate_pdf_from_batch_output
result = generate_pdf_from_batch_output(...)
```
