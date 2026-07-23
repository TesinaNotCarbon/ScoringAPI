# Scoring API

FastAPI service for environmental/reforestation scoring. It receives a project smart-contract address, reads its `cell_id` and previous scoring history from `ProjectManager`, resolves project geometry from IPFS/Pinata, reads satellite observations, and asks the LLM to return `scoring` and `fraud_scoring` values from `0.00` to `1.00`.

## Structure

```text
adapters/   Blockchain, IPFS, satellite, and Groq provider clients
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
- `BLOCKCHAIN_ADAPTER`: `mock` or `web3`.
- `RPC_URL`: EVM RPC URL when `BLOCKCHAIN_ADAPTER=web3`.
- `PROJECT_MANAGER_ADDRESS`: deployed ProjectManager contract address.
- `PROJECT_MANAGER_ABI_PATH`: path to the ProjectManager ABI JSON file.
- `GROQ_API_KEY`: Groq API key used by the LLM scoring adapter.
- `GROQ_MODEL`: Groq chat model, defaults to `llama-3.1-8b-instant`.
- `APPROVE_THRESHOLD`, `REVIEW_THRESHOLD`: legacy thresholds retained for compatibility.
- `DRASTIC_IMPROVEMENT_THRESHOLD`: legacy threshold retained for compatibility.
- `CORS_ORIGINS`: comma-separated allowed origins.

## Endpoints

- `GET /` health check.
- `GET /score/{project_id}` full scoring response. `project_id` must be an EVM address.
- `POST /score` full scoring response with `{ "project_id": "0x..." }`.
- `GET /chainlink/score/{project_id}` Chainlink-compatible response with `scoring` and `fraud_scoring` scaled to `0..100` integers.

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
