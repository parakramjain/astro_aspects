# reporting.layout

## Purpose
Core domain/business logic module.

## Public API
- `NumberedCanvas.draw_page_number`
- `NumberedCanvas.save`
- `NumberedCanvas.showPage`
- `build_doc`
- `date_range_label`
- `make_header_footer_drawer`
- `report_title_key`

## Internal Helpers
- `NumberedCanvas.__init__`

## Dependencies
- `__future__`
- `config`
- `dataclasses`
- `datetime`
- `i18n`
- `math`
- `normalize`
- `reportlab.lib.pagesizes`
- `reportlab.lib.units`
- `reportlab.pdfgen.canvas`
- `reportlab.platypus`
- `styles`
- `typing`

## Risks / TODOs
- No major heuristic risks detected.

## Example Usage
```python
from reporting.layout import NumberedCanvas
obj = NumberedCanvas(...)
result = obj.draw_page_number(...)
```
