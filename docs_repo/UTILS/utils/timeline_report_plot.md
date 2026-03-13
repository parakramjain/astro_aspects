# utils.timeline_report_plot

## Purpose
Shared utility/helper module.

## Public API
- `plot_timeline_gantt`
- `timeline_report_plot`

## Internal Helpers
- `_format_date`

## Dependencies
- `__future__`
- `ast`
- `datetime`
- `matplotlib.dates`
- `matplotlib.pyplot`
- `pytz`
- `schemas`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from utils.timeline_report_plot import plot_timeline_gantt
result = plot_timeline_gantt(...)
```
