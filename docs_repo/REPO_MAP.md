# Repo Map

Folder-by-folder Python ownership map.

## `.`
- Category mix: API=3, CORE=3, SCHEMAS=1
- `__init__.py` [CORE]
- `api_router.py` [API]
- `main.py` [API]
- `middleware.py` [API]
- `report_services.py` [CORE]
- `schemas.py` [SCHEMAS]
- `settings.py` [CORE]

## `aspect_card_utils`
- Category mix: API=1, CORE=7
- `aspect_card_utils/__init__.py` [CORE]
- `aspect_card_utils/aspect_card_creation.py` [CORE]
- `aspect_card_utils/aspect_card_creation_v0.py` [CORE]
- `aspect_card_utils/aspect_card_mgmt.py` [API]
- `aspect_card_utils/aspect_card_viewer.py` [CORE]
- `aspect_card_utils/aspect_report.py` [CORE]
- `aspect_card_utils/card_gen_ai.py` [CORE]
- `aspect_card_utils/vedic_kb.py` [CORE]

## `astro_core`
- Category mix: CORE=3
- `astro_core/__init__.py` [CORE]
- `astro_core/astro_core.py` [CORE]
- `astro_core/astro_services.py` [CORE]

## `automation`
- Category mix: TOOLS=4
- `automation/__init__.py` [TOOLS]
- `automation/batch_report_runner_daily.py` [TOOLS]
- `automation/batch_report_runner_full.py` [TOOLS]
- `automation/batch_report_runner_weekly.py` [TOOLS]

## `reporting`
- Category mix: CORE=7, SCHEMAS=2, TOOLS=1
- `reporting/__init__.py` [CORE]
- `reporting/cli.py` [TOOLS]
- `reporting/components.py` [CORE]
- `reporting/config.py` [SCHEMAS]
- `reporting/i18n.py` [CORE]
- `reporting/layout.py` [CORE]
- `reporting/normalize.py` [CORE]
- `reporting/renderer.py` [CORE]
- `reporting/schema.py` [SCHEMAS]
- `reporting/styles.py` [CORE]

## `reporting/builders`
- Category mix: CORE=8
- `reporting/builders/__init__.py` [CORE]
- `reporting/builders/appendix.py` [CORE]
- `reporting/builders/cover.py` [CORE]
- `reporting/builders/dashboard.py` [CORE]
- `reporting/builders/key_moments.py` [CORE]
- `reporting/builders/milestones.py` [CORE]
- `reporting/builders/summary.py` [CORE]
- `reporting/builders/timeline.py` [CORE]

## `reporting/tests`
- Category mix: TOOLS=3
- `reporting/tests/test_normalize.py` [TOOLS]
- `reporting/tests/test_renderer_smoke.py` [TOOLS]
- `reporting/tests/test_report_compact.py` [TOOLS]

## `services`
- Category mix: CORE=8, SCHEMAS=1
- `services/__init__.py` [CORE]
- `services/ai_agent_services.py` [CORE]
- `services/ai_prompt_service.py` [CORE]
- `services/natal_services.py` [CORE]
- `services/natal_services_v1_bkup.py` [CORE]
- `services/report_services.py` [CORE]
- `services/synastry_group_services.py` [SCHEMAS]
- `services/synastry_services.py` [CORE]
- `services/synastry_vedic_services.py` [CORE]

## `spend_intel_engine`
- Category mix: CORE=2
- `spend_intel_engine/__init__.py` [CORE]
- `spend_intel_engine/shopping_engine.py` [CORE]

## `spend_intel_engine/app`
- Category mix: CORE=2
- `spend_intel_engine/app/__init__.py` [CORE]
- `spend_intel_engine/app/shopping_score.py` [CORE]

## `spend_intel_engine/domain`
- Category mix: CORE=3
- `spend_intel_engine/domain/__init__.py` [CORE]
- `spend_intel_engine/domain/enums.py` [CORE]
- `spend_intel_engine/domain/models.py` [CORE]

## `spend_intel_engine/exporters`
- Category mix: CORE=2
- `spend_intel_engine/exporters/__init__.py` [CORE]
- `spend_intel_engine/exporters/shopping_insights_csv_exporter.py` [CORE]

## `spend_intel_engine/ops`
- Category mix: CORE=4
- `spend_intel_engine/ops/__init__.py` [CORE]
- `spend_intel_engine/ops/drift.py` [CORE]
- `spend_intel_engine/ops/logging.py` [CORE]
- `spend_intel_engine/ops/metrics.py` [CORE]

## `spend_intel_engine/rules`
- Category mix: CORE=2
- `spend_intel_engine/rules/__init__.py` [CORE]
- `spend_intel_engine/rules/loader.py` [CORE]

## `spend_intel_engine/scoring`
- Category mix: CORE=3
- `spend_intel_engine/scoring/__init__.py` [CORE]
- `spend_intel_engine/scoring/daily_scorer.py` [CORE]
- `spend_intel_engine/scoring/spend_profile_scorer.py` [CORE]

## `spend_intel_engine/tests`
- Category mix: TOOLS=10
- `spend_intel_engine/tests/conftest.py` [TOOLS]
- `spend_intel_engine/tests/test_aspect_normalization.py` [TOOLS]
- `spend_intel_engine/tests/test_cache.py` [TOOLS]
- `spend_intel_engine/tests/test_daily_scoring.py` [TOOLS]
- `spend_intel_engine/tests/test_fixtures.py` [TOOLS]
- `spend_intel_engine/tests/test_ops.py` [TOOLS]
- `spend_intel_engine/tests/test_purchase_type.py` [TOOLS]
- `spend_intel_engine/tests/test_shopping_insights_csv_exporter.py` [TOOLS]
- `spend_intel_engine/tests/test_spend_profile_scoring.py` [TOOLS]
- `spend_intel_engine/tests/test_vectorized_equivalence.py` [TOOLS]

## `spend_intel_engine/utils`
- Category mix: UTILS=5
- `spend_intel_engine/utils/__init__.py` [UTILS]
- `spend_intel_engine/utils/aspect_normalizer.py` [UTILS]
- `spend_intel_engine/utils/cache.py` [UTILS]
- `spend_intel_engine/utils/dates.py` [UTILS]
- `spend_intel_engine/utils/numbers.py` [UTILS]

## `tests`
- Category mix: API=1, SCHEMAS=1, TOOLS=2
- `tests/test_api_smoke.py` [API]
- `tests/test_ayanamsha.py` [TOOLS]
- `tests/test_upcoming_event_calendar.py` [TOOLS]
- `tests/test_upcoming_events_schema.py` [SCHEMAS]

## `tools`
- Category mix: TOOLS=1
- `tools/rename_sex_to_sxt.py` [TOOLS]

## `utils`
- Category mix: UTILS=11
- `utils/__init__.py` [UTILS]
- `utils/copy_to_s3.py` [UTILS]
- `utils/email_formatting_utils.py` [UTILS]
- `utils/email_util.py` [UTILS]
- `utils/llm_utils.py` [UTILS]
- `utils/report_generator.py` [UTILS]
- `utils/synastry_card_generation.py` [UTILS]
- `utils/text_utils.py` [UTILS]
- `utils/timeline_report_pdf.py` [UTILS]
- `utils/timeline_report_plot.py` [UTILS]
- `utils/timeline_report_text.py` [UTILS]

