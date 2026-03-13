# Changelog Notes (Documentation-driven)

Not a git changelog; this captures technical debt and refactor opportunities inferred from static analysis.

## Findings
- Risky functions: 73
- Needs refactor functions: 4
- API endpoints detected: 34

## Refactor opportunities
- `api_router:report_timeline` (risky): Risk: broad exception catch
- `api_router:daily_weekly` (risky): Risk: broad exception catch
- `api_router:compat_group` (risky): Risk: broad exception catch
- `aspect_card_utils.aspect_card_creation_v0:_load_life_event_mapping` (risky): Risk: broad exception catch; possible hardcoded secret/token
- `aspect_card_utils.aspect_card_creation_v0:write_cards` (risky): Risk: possible hardcoded secret/token
- `aspect_card_utils.aspect_card_mgmt:_parse_fields_param` (risky): Risk: possible hardcoded secret/token
- `aspect_card_utils.aspect_card_mgmt:list_cards_api` (risky): Risk: broad exception catch
- `aspect_card_utils.aspect_card_mgmt:admin_create_card` (risky): Risk: broad exception catch
- `aspect_card_utils.aspect_card_mgmt:admin_save_card` (risky): Risk: broad exception catch
- `aspect_card_utils.aspect_card_viewer:render_card_readonly` (risky): Risk: large function >80 LOC
- `aspect_card_utils.card_gen_ai:generate_aspect_card` (risky): Risk: broad exception catch; large function >80 LOC
- `astro_core.astro_core:calc_aspect_periods` (risky): Risk: large function >80 LOC
- `astro_core.astro_services:build_aspect_dict` (needs refactor): Refactor: excessive parameters
- `automation.batch_report_runner_daily:run_batch` (risky): Risk: broad exception catch
- `automation.batch_report_runner_full:run_batch` (risky): Risk: broad exception catch
- `automation.batch_report_runner_weekly:run_batch` (risky): Risk: broad exception catch
- `middleware:LoggingMiddleware.dispatch` (risky): Risk: broad exception catch
- `report_services:compute_life_events` (risky): Risk: broad exception catch; large function >80 LOC
- `report_services:compute_timeline` (risky): Risk: broad exception catch; large function >80 LOC; silent exception handling
- `reporting.builders.milestones:build_milestones_story` (risky): Risk: broad exception catch; large function >80 LOC
- `reporting.builders.timeline:_timeline_card` (risky): Risk: large function >80 LOC
- `reporting.builders.timeline:build_timeline_story` (risky): Risk: broad exception catch
- `reporting.normalize:parse_iso_datetime` (risky): Risk: broad exception catch; silent exception handling
- `reporting.normalize:safe_parse_stringified_dict` (risky): Risk: broad exception catch
- `reporting.renderer:generate_report_pdf` (risky): Risk: broad exception catch; large function >80 LOC
- `reporting.styles:build_styles` (risky): Risk: large function >80 LOC
- `services.ai_agent_services:calculate_token_cost` (risky): Risk: possible hardcoded secret/token
- `services.ai_agent_services:calculate_total_cost` (risky): Risk: possible hardcoded secret/token
- `services.ai_agent_services:generate_astrology_AI_summary` (risky): Risk: broad exception catch; possible hardcoded secret/token
- `services.ai_prompt_service:get_system_prompt_report` (risky): Risk: large function >80 LOC
- `services.ai_prompt_service:get_system_prompt_natal` (risky): Risk: large function >80 LOC
- `services.ai_prompt_service:get_system_prompt_weekly` (risky): Risk: large function >80 LOC
- `services.ai_prompt_service:get_user_prompt_daily` (risky): Risk: hardcoded URL
- `services.ai_prompt_service:get_user_prompt_weekly` (risky): Risk: hardcoded URL; large function >80 LOC
- `services.natal_services:planet_positions_and_houses` (risky): Risk: broad exception catch; large function >80 LOC
- `services.report_services:compute_life_events` (risky): Risk: broad exception catch; large function >80 LOC
- `services.report_services:compute_timeline` (risky): Risk: broad exception catch; large function >80 LOC; silent exception handling
- `services.report_services:upcoming_event` (risky): Risk: broad exception catch; large function >80 LOC
- `services.synastry_group_services:PersonInput.validate_timezone` (risky): Risk: broad exception catch
- `services.synastry_group_services:clamp_0_100` (risky): Risk: broad exception catch
- `services.synastry_group_services:scale_0_100` (risky): Risk: broad exception catch
- `services.synastry_group_services:z_score_to_0_100` (risky): Risk: broad exception catch
- `services.synastry_group_services:get_natal` (risky): Risk: broad exception catch
- `services.synastry_group_services:_pair_kpi_scores` (risky): Risk: broad exception catch
- `services.synastry_group_services:_cohesion_metrics` (risky): Risk: broad exception catch
- `services.synastry_group_services:_detect_outliers_cliques` (risky): Risk: broad exception catch
- `services.synastry_group_services:analyze_group` (risky): Risk: broad exception catch
- `services.synastry_group_services:_to_person_input` (risky): Risk: broad exception catch
- `services.synastry_vedic_services:koota_compatibility_status` (risky): Risk: broad exception catch
- `services.synastry_vedic_services:validate_input` (risky): Risk: broad exception catch
- `services.synastry_vedic_services:to_datetime_local` (risky): Risk: broad exception catch
- `services.synastry_vedic_services:to_utc` (risky): Risk: broad exception catch
- `services.synastry_vedic_services:compute_ashtakoota_score` (risky): Risk: large function >80 LOC
- `spend_intel_engine.exporters.shopping_insights_csv_exporter:export_shopping_insights_to_csv` (risky): Risk: large function >80 LOC
- `spend_intel_engine.ops.logging:log_shopping_run` (needs refactor): Refactor: excessive parameters
- `spend_intel_engine.scoring.daily_scorer:score_daily_shopping` (risky): Risk: large function >80 LOC
- `spend_intel_engine.scoring.daily_scorer:_add_moon_triggers` (needs refactor): Refactor: excessive parameters
- `spend_intel_engine.shopping_engine:compute_shopping_insights` (risky): Risk: large function >80 LOC
- `spend_intel_engine.tests.test_vectorized_equivalence:SampleLifeEvent.__init__` (needs refactor): Refactor: excessive parameters
- `spend_intel_engine.utils.aspect_normalizer:_canon_planet` (risky): Risk: possible hardcoded secret/token
- `spend_intel_engine.utils.aspect_normalizer:_canon_aspect` (risky): Risk: possible hardcoded secret/token
- `spend_intel_engine.utils.aspect_normalizer:normalize_aspect_code` (risky): Risk: possible hardcoded secret/token
- `tests.test_api_smoke:test_natal_characteristics_smoke` (risky): Risk: possible hardcoded secret/token
- `tools.rename_sex_to_sxt:rewrite_aspect_file` (risky): Risk: broad exception catch
- `tools.rename_sex_to_sxt:update_index_json` (risky): Risk: broad exception catch; silent exception handling
- `tools.rename_sex_to_sxt:main` (risky): Risk: broad exception catch
- `utils.copy_to_s3:upload_file_to_s3` (risky): Risk: possible hardcoded secret/token
- `utils.email_formatting_utils:render_basic_forecast_html_daily` (risky): Risk: hardcoded URL; large function >80 LOC
- `utils.email_formatting_utils:render_basic_forecast_html_weekly` (risky): Risk: hardcoded URL; large function >80 LOC
- `utils.llm_utils:get_token_encoder` (risky): Risk: possible hardcoded secret/token
- `utils.llm_utils:count_tokens` (risky): Risk: possible hardcoded secret/token
- `utils.llm_utils:count_response_tokens` (risky): Risk: possible hardcoded secret/token
- `utils.synastry_card_generation:SynastryPosterGenerator.generate` (risky): Risk: hardcoded URL; large function >80 LOC
- `utils.timeline_report_pdf:_get_devanagari_font_name` (risky): Risk: broad exception catch
- `utils.timeline_report_pdf:_get_cinzel_font_name` (risky): Risk: broad exception catch
- `utils.timeline_report_pdf:_format_ai_summary` (risky): Risk: broad exception catch
- `utils.timeline_report_pdf:create_timeline_pdf_report` (risky): Risk: large function >80 LOC

## Separate PR Suggestion (if code changes are desired)
- Introduce typed service boundaries and isolate side-effecting adapters.
- Add explicit timeout/retry wrappers for outbound network requests.
- Replace broad exception handlers with typed exceptions and structured logs.
- Standardize FastAPI response models and status codes.

## Improvement Priority Table
| Area | Findings | Recommendation | Priority |
|---|---|---|---|
| Functionality | Mixed concerns in service orchestration paths | Split validation/compute/render concerns | P1 |
| Performance/Scalability | Report generation and scoring may repeat expensive computations | Add cache strategy and workload chunking | P1 |
| Reliability/Security | Broad catches and potential timeout/secret hygiene gaps | Enforce exception policy, timeout defaults, and secret manager usage | P0 |
| Ops (logging/config/monitoring/deploy) | Inconsistent telemetry and config patterns | Define shared logging/metrics/config standards | P1 |
