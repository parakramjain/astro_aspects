# API Endpoints

| method | path | router | handler | request_model | response_model | auth | rate_limit | side_effects | external_calls |
|---|---|---|---|---|---|---|---|---|---|
| GET | / | app | `aspect_card_utils.aspect_card_mgmt:root_redirect` | - | - | unknown | not detected | none | none |
| GET | / | app | `main:landing` | - | - | unknown | not detected | none | none |
| GET | /admin | app | `aspect_card_utils.aspect_card_mgmt:admin_home` | - | - | unknown | not detected | none | none |
| GET | /admin/cards | app | `aspect_card_utils.aspect_card_mgmt:admin_cards_list` | - | - | unknown | not detected | none | none |
| POST | /admin/cards | app | `aspect_card_utils.aspect_card_mgmt:admin_create_card` | - | - | unknown | not detected | none | none |
| GET | /admin/cards/new | app | `aspect_card_utils.aspect_card_mgmt:admin_new_card` | - | - | unknown | not detected | filesystem | none |
| GET | /admin/cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:admin_edit_card` | - | - | unknown | not detected | db, filesystem | none |
| POST | /admin/cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:admin_save_card` | - | - | unknown | not detected | none | none |
| POST | /admin/cards/{card_id}/delete | app | `aspect_card_utils.aspect_card_mgmt:admin_delete_card` | - | - | unknown | not detected | db | none |
| GET | /admin/cards/{card_id}/view | app | `aspect_card_utils.aspect_card_mgmt:admin_view_card` | - | - | unknown | not detected | none | none |
| GET | /cards | app | `aspect_card_utils.aspect_card_mgmt:list_cards_api` | - | - | unknown | not detected | filesystem, network | none |
| POST | /cards | app | `aspect_card_utils.aspect_card_mgmt:create_card_api` | - | AspectCardModel | unknown | not detected | none | none |
| DELETE | /cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:delete_card_api` | - | - | unknown | not detected | db | none |
| GET | /cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:get_card_api` | - | AspectCardModel | unknown | not detected | none | none |
| PATCH | /cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:patch_card_api` | - | AspectCardModel | unknown | not detected | db, network | none |
| PUT | /cards/{card_id} | app | `aspect_card_utils.aspect_card_mgmt:replace_card_api` | - | AspectCardModel | unknown | not detected | none | none |
| GET | /cards/{card_id}/fields | app | `aspect_card_utils.aspect_card_mgmt:get_card_fields` | - | - | unknown | not detected | none | none |
| POST | /compat/ashtakoota | router | `api_router:compat_ashtakoota` | - | AshtakootaOut | unknown | not detected | none | none |
| POST | /compat/group | router | `api_router:compat_group` | - | GroupCompatibilityOut | unknown | not detected | none | none |
| POST | /compat/soulmate-finder | router | `api_router:soulmate_finder` | - | SoulmateOut | unknown | not detected | none | none |
| POST | /compat/synastry | router | `api_router:compat_pair` | - | CompatibilityOut | unknown | not detected | network | none |
| GET | /enums | app | `aspect_card_utils.aspect_card_mgmt:enums_api` | - | - | unknown | not detected | none | none |
| GET | /health | app | `aspect_card_utils.aspect_card_mgmt:health` | - | - | unknown | not detected | none | none |
| GET | /healthz | app | `main:healthz` | - | - | unknown | not detected | none | none |
| POST | /natal/aspects | router | `api_router:natal_aspects` | - | NatalAspectsOut | unknown | not detected | none | none |
| POST | /natal/build-chart | router | `api_router:build_natal_chart` | - | NatalChartOut | unknown | not detected | none | none |
| POST | /natal/characteristics | router | `api_router:natal_characteristics` | - | NatalCharacteristicsOut | unknown | not detected | none | none |
| POST | /natal/dignities-table | router | `api_router:dignities_table` | - | DignitiesOut | unknown | not detected | none | none |
| GET | /readyz | app | `main:readyz` | - | - | unknown | not detected | none | none |
| POST | /reports/daily-weekly | router | `api_router:daily_weekly` | - | DailyWeeklyOut | unknown | not detected | filesystem, logging | none |
| POST | /reports/life-events | router | `api_router:life_events` | - | LifeEventsOut | unknown | not detected | logging | none |
| POST | /reports/timeline | router | `api_router:report_timeline` | - | TimelineOut | unknown | not detected | filesystem, logging | none |
| POST | /reports/upcoming-events | router | `api_router:upcoming_events` | - | UpcomingEventsCalendarOut | unknown | not detected | logging | none |
| GET | /schema | app | `aspect_card_utils.aspect_card_mgmt:get_schema_api` | - | - | unknown | not detected | none | none |
