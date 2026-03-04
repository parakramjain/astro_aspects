# AstroSpend Intelligence Engine RunBook

## 1) Purpose
This runbook explains how to operate, validate, and troubleshoot the `spend_intel_engine` module in production and development.

---

## 2) Scope
Applies to:
- Spend profile scoring (`natal`)
- Daily shopping scoring (`transit/life-events`)
- Purchase-type aware scoring (`essentials`, `big_ticket`, `luxury`)
- Ruleset loading/caching
- Metrics and structured logging

Key entrypoint:
- `spend_intel_engine/shopping_engine.py`
- Main API function: `compute_shopping_insights(...)`

---

## 3) Prerequisites
- Python environment activated
- Dependencies installed from project `requirements.txt`
- CSV rule files available in `spend_intel_engine/data/` (or custom paths in `ShoppingCfg`)

Default rule CSV files:
- `natal_spend_aspects.csv`
- `transit_daily_shopping_aspects.csv`
- `natal_structure_signals.csv`
- `moon_spending_aspects.csv`

---

## 4) Quick Start

### A. Programmatic usage
```python
from datetime import date
from spend_intel_engine.domain.models import BirthPayload, ShoppingCfg
from spend_intel_engine.shopping_engine import compute_shopping_insights

payload = BirthPayload(
    name="Amit",
    dateOfBirth="1980-01-01",
    timeOfBirth="22:35:00",
    placeOfBirth="Mumbai, IN",
    timeZone="Asia/Kolkata",
    latitude=19.076,
    longitude=72.8777,
    lang_code="en",
)

cfg = ShoppingCfg(purchase_type="big_ticket")

insights = compute_shopping_insights(
    payload=payload,
    start_date=date(2026, 3, 1),
    n_days=14,
    cfg=cfg,
    purchase_type="big_ticket",  # optional; default = big_ticket
)
```

### B. CLI usage
```bash
python -m spend_intel_engine.app.shopping_score \
  --name "Amit" \
  --dob "1980-01-01" \
  --tob "22:35:00" \
  --place "Mumbai, IN" \
  --tz "Asia/Kolkata" \
  --lat 19.076 \
  --lon 72.8777 \
  --start-date "2026-03-01" \
  --n-days 14
```

---

## 5) Configuration Guide
Configuration model: `ShoppingCfg`

Important parameters:
- `purchase_type`: `essentials | big_ticket | luxury` (default: `big_ticket`)
- `daily_base_score`, `major_amplitude`, `minor_amplitude`
- `aspect_type_weights`, `event_type_weights`
- moon options:
  - `moon_trigger_enabled`
  - `moon_trigger_amplitude`
  - `moon_phase_by_date`

Optional override at call-site:
- `compute_shopping_insights(..., purchase_type="luxury")`
  - Overrides `cfg.purchase_type` for that run only.

---

## 6) Purchase-Type Behavior (Production Rules)

### Base amplitude multiplier
- `essentials`: `0.6`
- `big_ticket`: `1.0`
- `luxury`: `1.25`

### Risk multiplier for hard aspects (`SQR`, `OPP`)
- `essentials`: `0.7`
- `big_ticket`: `1.0`
- `luxury`: `1.4`

### Extra luxury penalty
If aspect is hard and contains `NEP` or `URA` or `PLU`, and `purchase_type == "luxury"`, apply additional `+20%` penalty.

### Behavioral guardrails
- If profile category is `Impulsive/High-Spend Risk` and `purchase_type == luxury`: reduce daily score by ~`7.5`.
- If profile category is `Ultra Thrifty` and `purchase_type == essentials`: raise daily baseline by `+3`.

### Advice appended to daily note
- `essentials`: `Safe for routine or necessary spending.`
- `big_ticket`: `Ensure planning and comparison before committing.`
- `luxury`: `Apply budget cap and cooling-off rule.`

---

## 7) Performance & Scalability

### Vectorized scoring
Daily scoring uses a vectorized event-day contribution matrix (`numpy/pandas`) to avoid nested `n_days × n_events` Python loops.

### Caching
- Rule maps are cached (`LRU`) at loader level.
- Natal structure features are cached by:
  - `chart_hash`
  - `ruleset_version`

### Ruleset versioning
`ruleset_version` = SHA256 hash over the 4 resolved rule CSV files.

### Horizon guard
If `n_days > 180`, scorer emits a warning recommending coarse weekly mode.

---

## 8) Observability & Metrics
`ShoppingInsights.metrics` contains:
- `ruleset_version`
- `n_days`
- `daily_score_mean`
- `daily_score_std`
- `positive_event_count`
- `negative_event_count`
- `mapped_aspect_ratio`
- `fallback_rate`
- `top_driver_frequencies` (top 10 aspect codes)

Structured JSON logging includes:
- `run_id`
- `user_hash` (hashed DOB+TOB+place)
- `ruleset_version`
- `purchase_type`
- `spend_profile_category`
- `fallback_rate`

PII policy:
- Raw PII is not logged by ops logging helpers.

---

## 9) Drift Detection
Helper function:
- `spend_intel_engine.ops.drift.detect_ruleset_shift(prev_distribution, current_distribution)`

Drift triggers:
- Mean shift > `8` points
- Std dev change > `20%`

Example:
```python
from spend_intel_engine.ops.drift import detect_ruleset_shift

prev = {"mean": 51.2, "std": 9.8}
curr = {"mean": 60.1, "std": 12.5}

is_shift = detect_ruleset_shift(prev, curr)
```

---

## 10) Validation & Test Commands
Run spend engine tests:
```bash
pytest spend_intel_engine/tests -q
```

Expected current status:
- All tests should pass (including purchase-type, vectorization equivalence, fallback-rate, and drift tests).

---

## 11) Troubleshooting

### Issue: CSV load errors
Symptoms:
- `ValueError` about missing columns

Actions:
1. Verify CSV headers exactly match expected columns.
2. Confirm paths in `ShoppingCfg`.
3. Ensure files are readable by runtime user.

### Issue: Unexpected score shifts
Actions:
1. Compare `ruleset_version` across runs.
2. Run `detect_ruleset_shift(...)` against baseline distribution.
3. Check `fallback_rate`; high fallback indicates weak mapping coverage.

### Issue: Low confidence days
Actions:
1. Inspect day `top_drivers`.
2. Check mapped ratio and major event counts.
3. Verify input event quality and aspect normalization.

### Issue: Long horizon latency
Actions:
1. Keep `n_days <= 180` where possible.
2. Split horizon into batches.
3. Consider weekly aggregation in orchestration layer.

---

## 12) Operational Checklist
Before release:
- [ ] `pytest spend_intel_engine/tests -q` passes
- [ ] Rule CSVs validated and versioned
- [ ] `ruleset_version` captured in logs
- [ ] Baseline score distribution snapshot updated
- [ ] Drift monitor thresholds confirmed

After release:
- [ ] Monitor `fallback_rate`
- [ ] Monitor `mapped_aspect_ratio`
- [ ] Monitor `daily_score_mean/std`
- [ ] Investigate detected shifts using ruleset diff + metrics

---

## 13) File Map (Quick Reference)
- Core orchestration: `spend_intel_engine/shopping_engine.py`
- Domain models/enums: `spend_intel_engine/domain/`
- Rules & hash/caching: `spend_intel_engine/rules/loader.py`
- Scoring logic: `spend_intel_engine/scoring/`
- Utilities: `spend_intel_engine/utils/`
- Ops/monitoring: `spend_intel_engine/ops/`
- Tests: `spend_intel_engine/tests/`
