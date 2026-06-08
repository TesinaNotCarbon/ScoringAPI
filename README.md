# Scoring API

Production-ready FastAPI service for environmental/reforestation scoring. It receives a `cell_id`, resolves project geometry from IPFS/Pinata, reads satellite observations through a provider interface, computes NDVI/SAVI/EVI/NBR, and returns a deterministic score suitable for Chainlink Functions or CRE.

## Structure

```text
api/        HTTP routes
core/       config, app factory, logging, exceptions
models/     Pydantic schemas
services/   IPFS, satellite provider, indicators and scoring logic
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

## Environment

Key variables:

- `ENVIRONMENT`: `local`, `test`, `staging`, or `production`.
- `PORT`: HTTP port.
- `PINATA_GATEWAY_BASE_URL`: Pinata/IPFS gateway base URL.
- `PINATA_JWT`: Pinata JWT. If omitted in `local`/`test`, a deterministic mock IPFS service is used.
- `APPROVE_THRESHOLD`, `REVIEW_THRESHOLD`: scoring thresholds.
- `CORS_ORIGINS`: comma-separated allowed origins.

## Endpoints

- `GET /` health check.
- `GET /score/{cell_id}` full scoring response.
- `POST /score` full scoring response with `{ "cell_id": "..." }`.
- `GET /chainlink/score/{cell_id}` compact `{ "score": number }` response.

## Tests

```bash
pytest
```

## Mock data

Local/test environments without `PINATA_JWT` use `services/mock_geojsons.json` through `MockIPFSService`.

Available sample cell ids:

- `healthy-forest-cell`
- `early-reforestation-cell`
- `degraded-soil-cell`
- `burned-area-cell`
- `cloudy-cell`

`MockSatelliteImageryProvider` reads `mock_satellite_profile` from GeoJSON properties and applies a deterministic geometry-based adjustment to spectral bands.

## Production notes

- Use a real `PINATA_JWT` and gateway in production.
- Keep satellite access behind `SatelliteImageryProvider` implementations.
- Do not log JWTs, private CIDs, full payloads, or sensitive coordinates.
- Configure reverse proxy/rate limiting/authentication according to deployment needs.
