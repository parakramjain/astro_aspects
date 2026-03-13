# Architecture

Inferred high-level architecture from Python code.

## Layers
- API layer: FastAPI entrypoints and router handlers.
- Core/service layer: astrology/reporting and spend intelligence orchestration.
- Schemas layer: Pydantic/model contract definitions.
- Tools layer: automation jobs, CLI, and tests.
- Utils layer: shared helper libraries.

## Execution patterns
- Request-driven HTTP flows.
- Batch report generation jobs.
- Reporting build-and-render pipeline.
- AI-assisted generation and prompt orchestration.

## MCP / tool-like functions
- `tools.rename_sex_to_sxt:find_root` in `tools/rename_sex_to_sxt.py`
- `tools.rename_sex_to_sxt:main` in `tools/rename_sex_to_sxt.py`
- `tools.rename_sex_to_sxt:rewrite_aspect_file` in `tools/rename_sex_to_sxt.py`
- `tools.rename_sex_to_sxt:update_index_json` in `tools/rename_sex_to_sxt.py`
