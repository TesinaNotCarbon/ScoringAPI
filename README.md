# Scoring API

FastAPI service for environmental/reforestation scoring. It receives a `cell_id`, resolves project geometry from IPFS/Pinata, reads satellite observations through a provider interface, computes NDVI/SAVI/EVI/NBR, and returns a deterministic score suitable for Chainlink Functions or CRE.

## Structure

```text
adapters/   IPFS, satellite, and Groq provider clients
api/        HTTP routes
core/       config, app factory, logging, exceptions
models/     Pydantic schemas
services/   indicators, fraud prevention, and scoring use cases
tests/      unit and integration tests
main.py     ASGI entrypoint
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The API listens on `PORT` or `3000` by default.

## Docker

Build and run with Docker:

```bash
docker build -t scoring-api .
docker run --rm -p 3000:3000 --env ENVIRONMENT=local scoring-api
```

Or use Docker Compose:

```bash
docker compose up --build
```

The container exposes port `3000` and includes a health check against `GET /`.

## Environment

Key variables:

- `ENVIRONMENT`: `local`, `test`, `staging`, or `production`.
- `PORT`: HTTP port.
- `PINATA_GATEWAY_BASE_URL`: Pinata/IPFS gateway base URL.
- `PINATA_JWT`: Pinata JWT. If omitted in `local`/`test`, a deterministic mock IPFS service is used.
- `SATELLITE_PROVIDER`: `mock` or `http`.
- `GROQ_API_KEY`: Groq API key used by the LLM fraud-analysis adapter.
- `GROQ_MODEL`: Groq chat model, defaults to `llama-3.1-8b-instant`.
- `APPROVE_THRESHOLD`, `REVIEW_THRESHOLD`: scoring thresholds.
- `DRASTIC_IMPROVEMENT_THRESHOLD`: max score increase before flagging suspicious improvement.
- `CORS_ORIGINS`: comma-separated allowed origins.

## Endpoints

- `GET /` health check.
- `GET /score/{cell_id}` full scoring response. Optionally pass `?previous_score=70&measurement_date=2026-07-15`.
- `POST /score` full scoring response with `{ "cell_id": "...", "previous_score": 70, "measurement_date": "2026-07-15" }`.
- `GET /chainlink/score/{cell_id}` deterministic Chainlink DON consensus response without free-text `description`. Optionally pass `?previous_score=70&measurement_date=2026-07-15`.

## Tests

```bash
pytest
```

## Mock data

Local/test environments without `PINATA_JWT` use `adapters/ipfs/mocks/mock_geojsons.json` through `MockIPFSService`.

Available sample cell ids:

- `healthy-forest-cell`
- `early-reforestation-cell`
- `degraded-soil-cell`
- `burned-area-cell`
- `cloudy-cell`

`MockSatelliteImageryProvider` reads profiles and cell-id mappings from `services/mocks/mock_satellite_profiles.json`, then applies deterministic geometry/date adjustments to spectral bands. The mock IPFS GeoJSONs only contain coordinates/geometry data.

## Production notes

- Use a real `PINATA_JWT` and gateway in production.
- Keep satellite access behind `SatelliteImageryProvider` implementations.
- Set `GROQ_API_KEY` for the production Groq AI adapter.
- Do not log JWTs, private CIDs, full payloads, or sensitive coordinates.
- Configure reverse proxy/rate limiting/authentication according to deployment needs.
