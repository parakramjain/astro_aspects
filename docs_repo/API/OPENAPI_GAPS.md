# OpenAPI Gaps

- Total endpoints: 34
- Missing `response_model`: 18
- Missing explicit status code declarations may exist; verify route decorators.
- Auth/rate-limit fields are static heuristic values.

## Endpoints Missing response_model
- `GET /` -> `aspect_card_utils.aspect_card_mgmt:root_redirect`
- `GET /` -> `main:landing`
- `GET /admin` -> `aspect_card_utils.aspect_card_mgmt:admin_home`
- `GET /admin/cards` -> `aspect_card_utils.aspect_card_mgmt:admin_cards_list`
- `POST /admin/cards` -> `aspect_card_utils.aspect_card_mgmt:admin_create_card`
- `GET /admin/cards/new` -> `aspect_card_utils.aspect_card_mgmt:admin_new_card`
- `GET /admin/cards/{card_id}` -> `aspect_card_utils.aspect_card_mgmt:admin_edit_card`
- `POST /admin/cards/{card_id}` -> `aspect_card_utils.aspect_card_mgmt:admin_save_card`
- `POST /admin/cards/{card_id}/delete` -> `aspect_card_utils.aspect_card_mgmt:admin_delete_card`
- `GET /admin/cards/{card_id}/view` -> `aspect_card_utils.aspect_card_mgmt:admin_view_card`
- `GET /cards` -> `aspect_card_utils.aspect_card_mgmt:list_cards_api`
- `DELETE /cards/{card_id}` -> `aspect_card_utils.aspect_card_mgmt:delete_card_api`
- `GET /cards/{card_id}/fields` -> `aspect_card_utils.aspect_card_mgmt:get_card_fields`
- `GET /enums` -> `aspect_card_utils.aspect_card_mgmt:enums_api`
- `GET /health` -> `aspect_card_utils.aspect_card_mgmt:health`
- `GET /healthz` -> `main:healthz`
- `GET /readyz` -> `main:readyz`
- `GET /schema` -> `aspect_card_utils.aspect_card_mgmt:get_schema_api`
