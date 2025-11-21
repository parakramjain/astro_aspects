# Astro Vision (Phase-1) — Technical Document

## 1. System Overview

Astro Vision — Core REST is a Python FastAPI backend that exposes astrology operations via JSON APIs. It relies on:

- **FastAPI / Starlette** for HTTP routing, validation, and middleware.
- **Pydantic v2** for request/response models in `schemas.py`.
- **Swiss Ephemeris (`swisseph`)** for planetary positions and house calculations, wrapped by `astro_core.astro_core` and `services.natal_services`.
- **A local knowledge base** of aspect cards (`kb/`) served and managed by a separate FastAPI app in `aspect_card_utils.aspect_card_mgmt`.

There is no database layer in this repository; all persistent data is file‑based (aspect card JSON, CSVs, index JSON).

### 1.1 Runtime Components

- **Core API Service**
  - Entry point: `main.py`.
  - Routers: `api_router.py` mounted under `/api`.
  - Deployed as a Uvicorn/ASGI app.

- **Aspect Card Admin + JSON API**
  - Entry point: `aspect_card_utils/aspect_card_mgmt.py` (separate FastAPI app, different port).
  - Purpose: CRUD for aspect cards and field-level JSON access (`/cards/{id}/fields`).

- **Domain Logic Modules**
  - `astro_core/astro_core.py` — core astronomical functions and aspect window extraction.
  - `services/natal_services.py` — natal chart calculations and natal aspect extraction.
  - `services/report_services.py` — life events, timelines, and daily/weekly processing.
  - `services/synastry_services.py` — pairwise synastry KPI logic.
  - `services/synastry_group_services.py` — group compatibility (2–10 people).
  - `services/synastry_vedic_services.py` — Vedic Ashtakoota calculation.

## 2. Architecture Diagram (Mermaid)

```mermaid
flowchart LR
  subgraph Client Apps
    A1[Web / Mobile]
    A2[Partner Services]
  end

  subgraph CoreAPI[Astro Vision Core REST (FastAPI)]
    M[main.py]
    R[api_router.py]
    S[schemas.py]
    SRV[services/*]
    AC[astro_core/astro_core.py]
  end

  subgraph AspectCards[Aspect Card Admin & JSON API]
    ACM[aspect_card_utils/aspect_card_mgmt.py]
    KB[kb/aspects/*.json\nkb/index.json]
  end

  subgraph ExternalDeps
    SE[(Swiss Ephemeris\n(pyswisseph))]
  end

  A1 -->|HTTP JSON| M
  A2 -->|HTTP JSON| M

  M --> R
  R --> SRV
  SRV --> AC
  AC --> SE

  SRV -->|get_card_fields()| ACM
  ACM --> KB
```

(Calls from `services.*` to aspect cards go through the Python function `get_card_fields` in `aspect_card_utils.aspect_card_mgmt`, which internally reads from the `kb` folder. In production this may be refactored to HTTP if the apps are separated; current implementation is in‑process.)

## 3. Tech Stack

- **Language**: Python 3.11+ (code uses `zoneinfo` and Pydantic v2).
- **Framework**: FastAPI + Starlette.
- **Data Validation**: Pydantic BaseModel (v2 style with `ConfigDict`).
- **Ephemeris**: Swiss Ephemeris via `pyswisseph` (`swisseph` module).
- **HTTP Server**: Uvicorn (ASGI).
- **Storage**:
  - JSON files in `kb/aspects` for aspect cards.
  - JSON index `kb/index.json` for card discovery.
  - CSVs in `kb/` for structured life-events mapping (`Life_Events_Aspects_structured.csv`, not directly wired in the scanned code).
- **Testing**: `pytest` (for `tests/test_api_smoke.py`) and `unittest` (for `tests/test_ayanamsha.py`).
- **Middleware Utilities**: Custom request ID and logging middleware in `middleware.py` (not fully expanded here but referenced in `main.py`).

## 4. Module Breakdown

### 4.1 `main.py`

- **Purpose**: ASGI entrypoint and lifecycle management.
- **Key responsibilities**:
  - Configure FastAPI app title, version, description.
  - Configure middleware:
    - `RequestIDMiddleware` — injects a `request_id` into `request.state` and headers.
    - `LoggingMiddleware` — request/response logging controlled by `REQUEST_LOGGING` mode.
    - CORS (`CORSMiddleware`) using `CORS_ALLOW_ORIGINS`.
    - GZip compression (`GZipMiddleware`).
    - Trusted hosts (`TrustedHostMiddleware`) using `TRUSTED_HOSTS`.
  - Configure exception handlers:
    - `RequestValidationError` → 422 with `ErrorResponse` envelope.
    - Generic `Exception` → 500 with `ErrorResponse` envelope.
  - Define health endpoints:
    - `GET /healthz` — liveness.
    - `GET /readyz` — readiness (currently a simple `{"ready": true}`; TODO to extend with deeper checks).
  - Include main router: `app.include_router(router)` where `router` is imported from `api_router.py`.

**Inputs → Outputs**:
- Inputs: HTTP requests (JSON payloads for POST, headers, query parameters).
- Outputs: JSON responses with `meta` and `data` or `error` fields.

**Dependencies**:
- `api_router` for business routes.
- `schemas.Meta`, `schemas.ErrorResponse`, `schemas.ErrorEnvelope`.
- `settings` for configuration.
- `middleware` for request ID and logging.

### 4.2 `settings.py`

- **Purpose**: Environment-driven configuration.
- **Key variables**:
  - `APP_NAME`, `APP_VERSION`.
  - `DEBUG` flag.
  - `CORS_ALLOW_ORIGINS`: comma-separated list or `*`.
  - `TRUSTED_HOSTS`: comma-separated list or `*`.
  - `GZIP_MIN_SIZE`.
  - `REQUEST_LOGGING`: `off` | `basic` | `full`.

### 4.3 `schemas.py`

- **Purpose**: Central definition of API contracts.

Key model groups:

- **Common**
  - `Meta` — response metadata.
  - `ErrorDetail`, `ErrorEnvelope`, `ErrorResponse` — uniform error format.

- **Inputs**
  - `BirthPayload` — used across natal, reports, and soulmate endpoints.
  - `PersonPayload` — used for compatibility.
  - `CompatibilityPairIn` — wrapper for `person1`, `person2`, `type`.
  - `GroupCompatibilityIn` — `people` (2–10) + `type` + optional `cursor`.
  - `TimelineRequest` — extends `BirthPayload` with `timePeriod`, `reportStartDate`, `cursor`.
  - `DailyWeeklyRequest` — extends `BirthPayload` with `mode`.
  - `LifeEventPayload` — extends `BirthPayload` with `start_date`, `horizon_days`.

- **Outputs (Natal)**
  - `PlanetEntry` → `NatalChartData` → `NatalChartOut`.
  - `DignityRow` → `DignitiesData` → `DignitiesOut`.
  - `NatalAspectItem` → `NatalAspectsOut`.
  - `KpiItem` → `NatalCharacteristicsData` → `NatalCharacteristicsOut`.

- **Outputs (Reports)**
  - `LifeEvent` → `LifeEventsOut`.
  - `TimelineItem` → `TimelineData` → `TimelineOut`.
  - `DailyArea` (currently unused `color` comment) → `DailyWeeklyData` → `DailyWeeklyOut`.
  - `UpcomingEventWindow`, `UpcomingEventRow` → `UpcomingEventsOut`.

- **Outputs (Compatibility)**
  - `KpiScoreRow`, `CompatibilityData`, `CompatibilityOut`.
  - `PairwiseRow`, `GroupCompatibilityData`, `GroupCompatibilityOut`.
  - `SoulmateData`, `SoulmateOut`.

- **Outputs (Vedic)**
  - `AshtakootaData`, `AshtakootaOut`.

- **Extended Group Models** (used within `synastry_group_services`):
  - `GroupSettings`, `PairwiseResult`, `GroupKPI`, `GroupResult`.

### 4.4 `api_router.py`

Defines all business endpoints under `APIRouter(prefix="/api")`.

#### 4.4.1 Meta Headers

- `MetaHeaders` dataclass with fields: `request_id`, `session_id`, `transaction_id`, `user_id`, `app_id`.
- `meta_headers_dep()` dependency reads HTTP headers (`X-Request-ID`, `X-Session-ID`, etc.) and populates `MetaHeaders`, generating UUIDs when absent.
- `build_meta()` converts `MetaHeaders` into `schemas.Meta` with current UTC ISO timestamp.

#### 4.4.2 Natal Endpoints

1. **POST `/api/natal/build-chart` → `NatalChartOut`**
   - Body: `BirthPayload`.
   - Logic: `calculate_natal_chart_data(payload)` from `services.natal_services`.
   - Output: `data.planets` list with sign, degree, and house details for each planet.

2. **POST `/api/natal/dignities-table` → `DignitiesOut`**
   - Body: `BirthPayload`.
   - Logic: Placeholder, returns table of planets with all dignity flags `False` and score `0.0`.
   - **Note**: Marked as placeholder in code; dignities logic is not implemented.

3. **POST `/api/natal/aspects` → `NatalAspectsOut`**
   - Body: `BirthPayload`.
   - Logic: `compute_natal_natal_aspects(payload)` from `services.natal_services`.
   - Enrichment: uses `get_card_fields` to fetch `core_meaning` and `facets` from aspect cards.

4. **POST `/api/natal/characteristics` → `NatalCharacteristicsOut`**
   - Body: `BirthPayload`.
   - Logic: Returns static narrative and three KPIs (Leadership, Communication, Resilience) as placeholders.
   - Comment: “Need to update below API to use aspect cards for characteristics.” (Future work.)

#### 4.4.3 Reports Endpoints

1. **POST `/api/reports/life-events` → `LifeEventsOut`**
   - Body: `LifeEventPayload`.
   - Parameters: `start_date` (string), `horizon_days` (int) in body.
   - Logic:
     - Parse `start_date` to `datetime.date` (400 error if invalid format).
     - Call `compute_life_events(payload, start_date, horizon_days)` from `services.report_services`, with fallback signature if older version.

2. **POST `/api/reports/timeline` → `TimelineOut`**
   - Body: `TimelineRequest`.
   - Logic:
     - Delegates to `compute_timeline(req)` in `services.report_services`.
     - Returns items with `description`, `keyPoints` (actionables), and `facets_points` based on aspect cards.

3. **POST `/api/reports/daily-weekly` → `DailyWeeklyOut`**
   - Body: `TimelineRequest` (reused; note: `DailyWeeklyRequest` model exists but is not used here).
   - Logic:
     - Calls `dailyWeeklyTimeline(req)` in `services.report_services`.

4. **POST `/api/reports/upcoming-events` → `LifeEventsOut`**
   - Body: `LifeEventPayload`.
   - Logic:
     - Same pattern as `life-events`; uses `compute_life_events` with given `start_date` and `horizon_days`.

#### 4.4.4 Compatibility Endpoints

1. **POST `/api/compat/synastry` → `CompatibilityOut`**
   - Body: `CompatibilityPairIn`.
   - Logic:
     - Extract Pydantic models into raw dicts and call `services.synastry_services.calculate_synastry`.
     - Build `KpiScoreRow` list from `syn["kpi_scores"]`: emotional, communication, chemistry, stability, elemental_balance.
     - Normalize each 0–10 score into 0–1 API `score` and derive short descriptions.
     - Compute total normalized score (`totalScore` 0–1) from `syn["total_score"]`.
     - Summary string references strongest KPI and top aspects.

2. **POST `/api/compat/group` → `GroupCompatibilityOut`**
   - Body: `GroupCompatibilityIn`.
   - Logic:
     - Validates `type` using `synastry_group_services.is_supported_type` inside `sg_build_group_api_payload`.
     - Delegates to `analyze_group_api_payload(people, type)`.
     - Output `data` is directly `GroupCompatibilityData(**api_data)`.

3. **POST `/api/compat/soulmate-finder` → `SoulmateOut`**
   - Body: `BirthPayload`.
   - Logic: Simple heuristic that returns birthdays ±1 and ±2 years from subject.

4. **POST `/api/compat/ashtakoota` → `AshtakootaOut`**
   - Body: `CompatibilityPairIn`.
   - Query parameters: `ayanamsa` (default `lahiri`), `coordinate_system` (`sidereal` or `tropical`), `strict_tradition` (bool), `use_exceptions` (bool).
   - Logic:
     - Extract Pydantic models to dicts.
     - Call `compute_ashtakoota_score` and `explain_ashtakoota` from `services.synastry_vedic_services`.

## 5. Core Logic Flows

### 5.1 Natal Chart Build

1. `api_router.build_natal_chart` receives `BirthPayload`.
2. `services.natal_services.calculate_natal_chart_data`:
   - Calls `planet_positions_and_houses` with `house_system="WHOLE"`.
   - `planet_positions_and_houses`:
     - Configures ayanamsa via `astro_core.set_ayanamsha` (default sidereal Lahiri).
     - Builds local datetime from `dateOfBirth`, `timeOfBirth`, and `timeZone` using `zoneinfo.ZoneInfo`.
     - Converts to UTC and computes planetary longitudes using `astro_core._planet_longitudes_utc`, which wraps `swisseph.calc_ut`.
     - Computes Ascendant and cusps via `_asc_mc_and_cusps_utc` and `_houses_compat`.
     - Assigns house numbers based on Whole Sign or quadrant logic.
   - For each planet:
     - Converts longitude to sign and intra-sign degree via `lon_to_sign_deg_min`.
     - Maps to `houseNumber`, `houseName` (First House, etc.), and `houseSign`.
   - Returns `NatalChartData(planets=...)`.

### 5.2 Natal Aspect Extraction

1. `api_router.natal_aspects` receives `BirthPayload`.
2. `services.natal_services.compute_natal_natal_aspects`:
   - Calls `planet_positions_and_houses` to get positions.
   - Extracts longitudes.
   - Iterates over unique pairs of planets:
     - Computes separation angle (0–180 deg) and checks against each aspect angle defined in `astro_core.ASPECTS`.
     - Uses `astro_core.NATAL_ASPECT_ORB_DEG` to determine valid orb (e.g., up to 15° for trines).
     - Calculates `strength = 1 - dist/orb`.
     - Builds aspect label `"Moo CON Sun"`, etc.
     - Looks up aspect card via `get_card_fields(f"{A}_{code}_{B}__v1.0.0", fields="core_meaning,facets")`.
   - Returns sorted list of `NatalAspectItem` with `characteristics` containing aspect card fields.

### 5.3 Life Events & Timeline

**Life Events (`compute_life_events`)**

1. Determine anchor date (`start_date` or `today`).
2. Compute `end = anchor + horizon_days`.
3. Call `astro_core.calc_aspect_periods` with:
   - `birth_date`, `birth_time`, `birth_tz` from `BirthPayload`.
   - `start_date`, `end_date` range.
   - `sample_step_hours` default 6.
4. For each `AspectPeriod`:
   - Identify transit planet (`t`), aspect code (`a`), natal planet (`n`).
   - Determine eventType (`MAJOR` if transit planet is Jupiter–Pluto, else `MINOR`).
   - Build `card_id` from `PLANET_CODE_MAP` and `ASPECT_CODE_MAP` (e.g., `JUP_CON_SUN__v1.0.0`).
   - Fetch `life_event_type` from aspect card via `get_card_fields(card_id, fields="life_event_type")`.
   - Normalize `life_event_type` (list or dict) to description text; fallback to a generic phrase if missing.
   - Build `LifeEvent` objects.

**Timeline (`compute_timeline`)**

1. Interpret `req.timePeriod` to decide `end`, `sample_step_hours`, and `planet_exclusion_list`.
2. Call `calc_aspect_periods` with adjusted sampling and optional `exclude_transit_short` (e.g., exclude fast planets for long horizons).
3. For each `AspectPeriod`:
   - Build `card_id` and call `get_card_fields(card_id, fields="locales.hi.core,core_meaning,facets,actionables")`.
   - Prefer `locales.hi.core` for description, fallback to `core_meaning`.
   - Extract `actionables` into `keyPoints` (dict mapping phase → list of strings).
   - Extract `facets` into `facets_points` (dict mapping facet → description string).
4. Compose `TimelineItem` list and `aiSummary` text summarizing count and period.

**Daily/Weekly (`dailyWeeklyTimeline`)**

1. Call `compute_timeline` for the requested period.
2. Aggregate `facets_points` from `TimelineItem` objects into an `areas` dict:
   - For each `facets_points` key/value, append to `areas[key]` as list.
3. Return `DailyWeeklyData(shortSummary=..., areas=areas)`.

### 5.4 Synastry Scoring

1. `api_router.compat_pair` receives `CompatibilityPairIn`.
2. `services.synastry_services.calculate_synastry`:
   - `_parse_person_input` converts incoming dicts to kwargs for `astro_core.calc_planet_pos`.
   - Computes planetary positions (`pos1`, `pos2`).
   - `calculate_planetary_angles` uses `astro_core.ASPECTS` and `NATAL_ASPECT_ORB_DEG` to find cross-aspects and their orbs.
   - `get_natal_characteristics` derives sign-based element and modality balances, temperament, and dominant element/modality.
   - `calculate_compatibility_scores` computes KPI scores (0–10):
     - Emotional: Moon–Venus, Moon–Moon.
     - Communication: Mercury–Mercury, Mercury–Moon.
     - Chemistry: Venus–Mars, Venus–Sun.
     - Stability: Saturn–Sun, Saturn–Moon.
     - Elemental balance: difference between elemental distributions.
   - Weighted total score is computed using `KPI_WEIGHTS`.
   - Returns structure with aspects, traits, `kpi_scores`, `total_score`, and baseline.
3. `api_router.compat_pair` normalizes and shapes `CompatibilityOut`.

### 5.5 Group Compatibility Flow

1. `api_router.compat_group` receives `GroupCompatibilityIn`.
2. `services.synastry_group_services.analyze_group_api_payload`:
   - Validates `type` and person count (2–10).
   - Converts inputs to `PersonInput` (extends `BirthPayload`).
   - Calls `analyze_group`:
     - For each unordered pair, calls `compute_pair`:
       - Uses `get_natal` with LRU cache to avoid recomputing natals.
       - Uses `_pair_kpi_scores` to map synastry KPIs to group KPIs (`DEFAULT_KPIS`).
       - Computes total pair score (0–100) using `TYPE_KPI_WEIGHTS` per compatibility type.
       - Builds `PairwiseResult` (person1, person2, kpi_scores dict, total_pair_score, description).
     - Aggregates group KPIs via `_aggregate_group_kpis`.
     - Computes cohesion metrics (`_cohesion_metrics`) and `total_group_score`.
     - Produces a summary and a shareable card payload.
   - `analyze_group_api_payload` then normalizes scores to 0–1 for API and flattens best KPIs and descriptions.
3. `api_router.compat_group` wraps this in `GroupCompatibilityOut`.

### 5.6 Vedic Ashtakoota Flow

1. `api_router.compat_ashtakoota` receives `CompatibilityPairIn` and query parameters.
2. `services.synastry_vedic_services.compute_ashtakoota_score`:
   - Validates input structure and coordinates.
   - Converts birth info into localized datetimes and UTC using `zoneinfo`.
   - Calls `astro_core.calc_planet_pos` with specified `ayanamsa` and `coordinate_system` to get Moon longitude.
   - Derives Moon rashi, nakshatra index, and pada.
   - Calculates scores for each koota:
     - `score_varna`, `score_vashya`, `score_tara`, `score_yoni`, `score_graha_maitri`, `score_gana`, `score_bhakoot`, `score_nadi`.
   - Aggregates and rounds scores in `sum_scores` (total 0–36).
   - Interprets total in `interpret_total_score` to band plus advice.
3. `explain_ashtakoota` builds a multi-line explanation string used in `AshtakootaData.explanation`.

## 6. Data Models / Schemas

See `schemas.py` for full definitions; high-level:

- **AspectCard JSON Schema** (informal, from `AspectCardModel`):

  ```jsonc
  {
    "id": "JUP_CON_MOO__v1.0.0", // 3-letter planet codes + aspect + version
    "pair": ["Jupiter", "Conjunction", "Moon"],
    "applies_to": ["natal", "transit", "progressed"],
    "core_meaning": "..." or {"en": "...", "hi": "..."},
    "facets": {"career": "..." or {"en": "...", "hi": "..."}, ...},
    "life_event_type": ["...", "..."] or {"en": [...], "hi": [...]},
    "risk_notes": ..., "actionables": {"applying": [...], "exact": [...], "separating": [...]},
    "keywords": ..., "quality_tags": ..., "weights_hint": {}, "modifiers": {},
    "theme_overlays": ..., "refs": [], "provenance": {},
    "locales": {"en": {"title": "...", "core": "...", "tone": "..."}, ...},
    "retrieval": {"embedding_sections": {"core": "...", ...}, "aliases": []}
  }
  ```

- **Meta / Error**:
  - `Meta.timestamp`: ISO 8601 with `Z`.
  - `ErrorEnvelope.code`: e.g., `SERVER_ERROR`, `UNPROCESSABLE_ENTITY`.

- **Enums/Constants**:
  - Aspect codes: `Con`, `Sxt`, `Sqr`, `Tri`, `Opp` (`astro_core.ASPECTS`).
  - Ayanamsha names: `Lahiri`, `Raman`, `Krishnamurti`, `Yukteshwar`, `Sassanian`, `GalacticCenter`, `USER` (`astro_core.AYANAMSHA_MAP`).
  - Compatibility group types: `Friendship Group`, `Professional Team`, `Sport Team`, `Family`, `Relative` (`synastry_group_services.CompatibilityType`).

## 7. Configuration & Environments

### 7.1 Environment Variables (from `README.md` and `settings.py`)

| Variable           | Default                           | Purpose |
|--------------------|-----------------------------------|---------|
| `APP_NAME`         | `Astro Vision — Core REST`        | FastAPI title. |
| `APP_VERSION`      | `1.0.0`                           | API version and meta field. |
| `DEBUG`            | `false`                           | Enables debug mode in settings (used by logging). |
| `CORS_ALLOW_ORIGINS` | `*`                             | Allowed CORS origins (comma-separated). |
| `TRUSTED_HOSTS`    | `*`                               | Allowed hostnames for `TrustedHostMiddleware`. |
| `GZIP_MIN_SIZE`    | `1000`                            | Byte threshold for GZip compression. |
| `REQUEST_LOGGING`  | `basic`                           | `off` | `basic` | `full` for LoggingMiddleware. |
| `GROUP_SYN_LOG`    | `info`                            | Logging level for `synastry_group_services`. |

No `.env` or Docker files are present in the scanned structure; environment management is assumed to be external. *(Assumption (verify).)*

### 7.2 Dev vs Prod

- **Dev**: typically run via `python main.py` with Uvicorn reload and permissive CORS/trusted hosts.
- **Prod**: run under a managed Uvicorn/Gunicorn process with tightened `CORS_ALLOW_ORIGINS`, `TRUSTED_HOSTS`, and `REQUEST_LOGGING`.

Switching between sidereal and tropical modes or ayanamsa is done per call or globally via `astro_core.set_ayanamsha` but is primarily managed by service functions (`natal_services`, `synastry_vedic_services`).

## 8. Storage / Knowledge Base

- **Aspect Cards**: JSON files under `kb/aspects` indexed by `kb/index.json`.
- **Index**: `index.json` lists all cards with `id`, `pair`, and `path`.
- **Access Pattern**:
  - `aspect_card_utils.aspect_card_mgmt.load_card()` loads a card from disk with file locking via `portalocker` (Windows-friendly).
  - `get_card_fields(card_id, fields=...)` returns a subset of fields; used heavily by `services.natal_services` and `services.report_services`.

There is no relational database or vector store instantiated in this code. *(Assumption (verify): future versions may add vector search using `retrieval.embedding_sections`.)*

## 9. External Integrations

- **Swiss Ephemeris** (`swisseph`)
  - Used in `astro_core.astro_core` and `services.natal_services`.
  - Functions: `swe.calc_ut`, `swe.houses_ex`, `swe.houses`, `swe.set_sid_mode`.
  - Must be installed and Ephemeris data files must be accessible via `swe.set_ephe_path`.

- **Time Zones**
  - Python standard `zoneinfo` is used throughout for time zone handling.

- **No LLM / Translation API Calls**
  - While aspect cards support bilingual content, the data is local; there is no runtime call to translation services or LLM providers in this codebase.

- **No Messaging / Email Integrations**
  - The repo does not include WhatsApp/email/SMS connectors.

## 10. Security & Compliance

- **Authentication / Authorization**: Not implemented in this repo. The API is unauthenticated by default. *(Assumption (verify): deploy behind an API gateway or auth proxy.)*
- **Rate Limiting / Abuse Protection**: Not implemented.
- **PII Handling**:
  - Inputs include names, birth data, and locations, which are PII.
  - No encryption at rest is visible (KB is non-PII; request data is transient).
  - Responsibility for logging redaction and secure transport (HTTPS) falls on deployment configuration.
- **Multi-Tenancy**: There is no tenant segmentation in the code; `X-App-ID` and `X-User-ID` headers exist for traceability only.

## 11. Observability & Ops

- **Logging**:
  - `LoggingMiddleware` in `middleware.py` logs requests based on `REQUEST_LOGGING` mode (`off`, `basic`, `full`).
  - `synastry_group_services` has its own logger with level from `GROUP_SYN_LOG`.

- **Health Checks**:
  - `GET /healthz` (simple) and `GET /readyz` (placeholder) are available for container orchestrators.

- **Error Handling**:
  - Uniform error envelope via exception handlers in `main.py`.

- **CI/CD & Docker**:
  - No Dockerfile or CI configuration present in the repository snapshot. *(Assumption (verify).)*

## 12. Testing

### 12.1 Test Structure

- `tests/test_api_smoke.py`
  - Uses `fastapi.testclient.TestClient` on `main.app`.
  - Currently includes a smoke test for `/api/natal/characteristics` to ensure 200 status and presence of `description` and `kpis`.

- `tests/test_ayanamsha.py`
  - Uses `unittest` to test:
    - Sidereal vs tropical Sun longitude difference for a reference date.
    - Custom `USER` ayanamsa offset.

There are no explicit tests for lifecycle endpoints, reports, or compatibility flows yet. *(Assumption (verify): more tests may exist in other branches.)*

### 12.2 How to Run Tests

From the repo root:

```powershell
python -m pip install -r .\requirements.txt
pytest
```

`tests/test_ayanamsha.py` can also be run directly via `python tests/test_ayanamsha.py`.

## 13. Known Gaps / Tech Debt

Derived from TODOs and placeholders in the code:

- **Natal Characteristics** — `/api/natal/characteristics` currently returns a hard-coded narrative; TODO to integrate with aspect cards or ML models.
- **Dignities Table** — `/api/natal/dignities-table` returns dummy values; real dignities and essential scores must be implemented.
- **Timeline Summary** — `TimelineData.aiSummary` is a simple string summarizing count and period; could be replaced with rich narrative generation.
- **DailyWeekly Areas** — `DailyWeeklyData.areas` is a dict of lists populated directly from facet strings, with no scoring or prioritization.
- **Group Synastry Optional Dependencies** — `synastry_group_services` optionally uses `numpy` and `networkx`. If unavailable, metrics degrade gracefully but network-based cohesion metrics are not computed.
- **Error Messages & Localization** — Error responses are English-only; no localization framework is in place.

## 14. Appendix

### 14.1 Trimmed Repo Tree

```text
astro_aspects/
  main.py
  api_router.py
  schemas.py
  settings.py
  middleware.py
  README.md
  aspect_card_utils/
    aspect_card_mgmt.py
    aspect_card_viewer.py
    aspect_card_creation.py
    aspect_report.py
    vedic_kb.py
  astro_core/
    astro_core.py
    astro_services.py
  services/
    natal_services.py
    report_services.py
    synastry_services.py
    synastry_group_services.py
    synastry_vedic_services.py
  kb/
    index.json
    aspects/*.json
  tests/
    test_api_smoke.py
    test_ayanamsha.py
  tools/
    rename_sex_to_sxt.py
  docs/
    AstroVision_Business_Document.md
    AstroVision_Technical_Document.md
```

### 14.2 Command Cheatsheet

**Install dependencies** (Windows PowerShell):

```powershell
python -m pip install -r .\requirements.txt
```

**Run Core API**:

```powershell
python .\main.py
# or
uvicorn main:app --host 127.0.0.1 --port 8787 --reload
```

**Open API Docs**:

- http://127.0.0.1:8787/docs

**Run Aspect Card Admin App**:

```powershell
python -m uvicorn aspect_card_utils.aspect_card_mgmt:app --reload --host 127.0.0.1 --port 8788
```

Admin UI: http://127.0.0.1:8788/admin

**Run Tests**:

```powershell
pytest
```

(Ensure `pyswisseph` and ephemeris data files are installed and accessible for tests involving `astro_core`.)
