# Career Intent

Production-ready, deterministic Career Timing Intelligence module.

## Run API

```bash
uvicorn career_intent.app.main:app --reload --port 8010
```

## API Endpoints

- `GET /health`
- `POST /v1/career/insight`
- `POST /v1/career/report?format=html|pdf`

## Batch Runner

```bash
python -m career_intent.app.batch.runner --csv <input.csv> --outdir <dir> --months 6 --format html
```

## Input CSV Columns

`name,dateOfBirth,timeOfBirth,placeOfBirth,timeZone,latitude,longitude,lang_code,career_intent`

Optional timeframe columns:

`start_date,end_date,months`

## Tests

```bash
pytest career_intent/tests -q
```
