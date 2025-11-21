# Astro Vision — Core REST

FastAPI-based backend service exposing Natal, Reports, and Compatibility APIs for the Astro Vision engine.

## Overview

Astro Vision — Core REST is a headless astrology engine. It computes natal charts, life-event timelines, and relationship compatibility using Swiss Ephemeris-based calculations plus a file-backed knowledge base of "aspect cards" stored under `kb/`.

The service exposes a JSON API (documented in `API_defination.yaml`) that frontends, other microservices, and partner systems can call to:

- Build natal charts by sign and house from birth data.
- Generate life events and timelines from transit-to-natal aspect windows.
- Compute Western synastry for pairs and groups.
- Calculate Vedic Ashtakoota (Gun Milan) compatibility scores.

Most responses are wrapped in a consistent `meta` + `data` envelope using Pydantic models in `schemas.py`. Health endpoints (`/healthz`, `/readyz`) are provided for orchestration.

## Features

- **Natal**
	- `POST /api/natal/build-chart` — compute planets with zodiac sign, intra-sign degree, and house (Whole Sign houses).
	- `POST /api/natal/aspects` — list natal aspects, enriched with aspect card meanings and facets.
	- `POST /api/natal/characteristics` — high-level personality description and KPIs (currently placeholder text).

- **Reports**
	- `POST /api/reports/life-events` — generate major/minor life events from transit-to-natal aspect periods.
	- `POST /api/reports/timeline` — build a timeline of aspect windows with descriptions, key points, and facets.
	- `POST /api/reports/daily-weekly` — aggregate facets into themed daily/weekly areas.
	- `POST /api/reports/upcoming-events` — short-horizon version of life events.

- **Compatibility**
	- `POST /api/compat/synastry` — pairwise Western synastry KPIs and total score.
	- `POST /api/compat/group` — group compatibility (2–10 people) with group KPIs and pairwise rows.
	- `POST /api/compat/soulmate-finder` — simple DOB suggestion heuristic around the subject's birth year.
	- `POST /api/compat/ashtakoota` — Vedic Ashtakoota (Gun Milan) score and explanation.

- **Knowledge Base / Admin**
	- Aspect cards (`kb/aspects/*.json`) managed by the separate admin app `aspect_card_utils/aspect_card_mgmt.py`.
	- Core API services call `get_card_fields(...)` to fetch card fields such as `core_meaning`, `facets`, `life_event_type`, and `actionables`.

## What's included

- `main.py`: FastAPI app with production middleware (CORS, GZip, TrustedHosts, Request ID, basic request logging) and uniform error envelopes.
- `api_router.py`: All `/api` endpoints for Natal, Reports, and Compatibility.
- `schemas.py`: Pydantic models mirroring the OpenAPI components.
- `settings.py`: Basic environment-driven configuration.
- `middleware.py`: Request ID + logging middleware.
- `astro_core/`: Core astronomical and aspect-period logic.
- `services/`: Natal, reports, synastry, group, and Vedic service layers.

Existing domain logic is reused when present (e.g., planet positions, aspect periods, synastry scoring). Where features aren't implemented yet, handlers return typed placeholder data so clients can integrate now.

## Run locally

Install deps (Windows PowerShell):

```powershell
python -m pip install -r .\requirements.txt
```

Start the API locally on port 8787:

```powershell
python .\main.py
```

Or with Uvicorn directly:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8787 --reload
```

Open docs at http://127.0.0.1:8787/docs

## Env configuration

- `APP_NAME` (default: "Astro Vision — Core REST")
- `APP_VERSION` (default: "1.0.0")
- `CORS_ALLOW_ORIGINS` comma-separated or `*`
- `TRUSTED_HOSTS` comma-separated or `*`
- `GZIP_MIN_SIZE` bytes threshold (default: 1000)
- `REQUEST_LOGGING` off|basic|full

## Health

- `GET /healthz` liveness
- `GET /readyz` readiness (extend with deeper checks if needed)

## Notes

- The service currently uses Whole Sign houses for natal chart display.
- Dignities, characteristics, and compatibility are placeholders; wire them to your knowledge base and scoring when ready.
- Existing `aspect_card_mgmt.py` admin app remains separate and untouched.
