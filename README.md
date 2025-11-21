# Astro Vision — Core REST

FastAPI service exposing Natal, Reports, and Compatibility APIs defined in `API_defination.yaml`.

## What's included

- `main.py`: FastAPI app with production middleware (CORS, GZip, TrustedHosts, Request ID, basic request logging) and uniform error envelopes.
- `api_router.py`: All endpoints under `/v1` mapped from `API_defination.yaml`.
- `schemas.py`: Pydantic models mirroring the OpenAPI components.
- `settings.py`: Basic environment-driven configuration.
- `middleware.py`: Request ID + logging middleware.

Existing domain logic is reused when present (e.g., planet positions, aspect periods). Where features aren't implemented yet, handlers return typed placeholder data so clients can integrate now.

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
