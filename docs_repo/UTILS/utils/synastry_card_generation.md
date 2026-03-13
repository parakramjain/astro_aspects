# utils.synastry_card_generation

## Purpose
Shared utility/helper module.

## Public API
- `SynastryPosterGenerator.generate`

## Internal Helpers
- `SynastryPosterGenerator.__init__`
- `SynastryPosterGenerator._draw_gauge`
- `SynastryPosterGenerator._draw_radar_chart`
- `SynastryPosterGenerator._get_gradients_and_filters`

## Dependencies
- `json`
- `math`
- `os`
- `services.synastry_services`
- `sys`

## Risks / TODOs
- `SynastryPosterGenerator.generate`: risky (Risk: hardcoded URL; large function >80 LOC)

## Example Usage
```python
from utils.synastry_card_generation import SynastryPosterGenerator
obj = SynastryPosterGenerator(...)
result = obj.generate(...)
```
