# aspect_card_utils.aspect_card_mgmt

## Purpose
API layer module exposing request handlers and routing.

## Public API
- `admin_cards_list`
- `admin_create_card`
- `admin_delete_card`
- `admin_edit_card`
- `admin_home`
- `admin_new_card`
- `admin_save_card`
- `admin_view_card`
- `card_path`
- `create_card_api`
- `delete_card`
- `delete_card_api`
- `ensure_dirs`
- `enums_api`
- `get_card_api`
- `get_card_fields`
- `get_schema_api`
- `health`
- `list_card_ids`
- `list_cards_api`
- `load_card`
- `page`
- `patch_card_api`
- `render_table`
- `replace_card_api`
- `root_redirect`
- `save_card`

## Internal Helpers
- `AspectCardModel._id_format`
- `AspectCardModel._pair_format`
- `_assign_by_path`
- `_get_by_path`
- `_parse_fields_param`
- `_select_fields_dict`
- `_select_lang_from_value`

## Dependencies
- `__future__`
- `aspect_card_viewer`
- `datetime`
- `fastapi`
- `fastapi.middleware.cors`
- `fastapi.responses`
- `glob`
- `json`
- `os`
- `portalocker`
- `pydantic`
- `re`
- `typing`

## Risks / TODOs
- `_parse_fields_param`: risky (Risk: possible hardcoded secret/token)
- `list_cards_api`: risky (Risk: broad exception catch)
- `admin_create_card`: risky (Risk: broad exception catch)
- `admin_save_card`: risky (Risk: broad exception catch)

## Example Usage
```python
from aspect_card_utils.aspect_card_mgmt import admin_cards_list
result = admin_cards_list(...)
```

## Endpoints
- `GET /health` handled by `aspect_card_utils.aspect_card_mgmt:health`
- `GET /` handled by `aspect_card_utils.aspect_card_mgmt:root_redirect`
- `GET /cards` handled by `aspect_card_utils.aspect_card_mgmt:list_cards_api`
- `GET /cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:get_card_api`
- `GET /cards/{card_id}/fields` handled by `aspect_card_utils.aspect_card_mgmt:get_card_fields`
- `POST /cards` handled by `aspect_card_utils.aspect_card_mgmt:create_card_api`
- `PUT /cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:replace_card_api`
- `PATCH /cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:patch_card_api`
- `DELETE /cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:delete_card_api`
- `GET /schema` handled by `aspect_card_utils.aspect_card_mgmt:get_schema_api`
- `GET /enums` handled by `aspect_card_utils.aspect_card_mgmt:enums_api`
- `GET /admin` handled by `aspect_card_utils.aspect_card_mgmt:admin_home`
- `GET /admin/cards` handled by `aspect_card_utils.aspect_card_mgmt:admin_cards_list`
- `GET /admin/cards/new` handled by `aspect_card_utils.aspect_card_mgmt:admin_new_card`
- `POST /admin/cards` handled by `aspect_card_utils.aspect_card_mgmt:admin_create_card`
- `GET /admin/cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:admin_edit_card`
- `GET /admin/cards/{card_id}/view` handled by `aspect_card_utils.aspect_card_mgmt:admin_view_card`
- `POST /admin/cards/{card_id}` handled by `aspect_card_utils.aspect_card_mgmt:admin_save_card`
- `POST /admin/cards/{card_id}/delete` handled by `aspect_card_utils.aspect_card_mgmt:admin_delete_card`
