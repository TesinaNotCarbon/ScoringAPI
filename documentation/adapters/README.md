# Adapters

Infrastructure adapters live under `adapters/` so application services can stay focused on use cases and scoring logic.

## Folder layout

```text
adapters/
  ai/             Groq LLM adapter and AI provider protocol
  ipfs/           Pinata/IPFS client
    mocks/        local deterministic IPFS mock and mock GeoJSON data
  satellite/      satellite provider protocol, HTTP client, and satellite mock
```

## IPFS adapter

Files:

- `adapters/ipfs/service.py`
- `adapters/ipfs/mocks/service.py`
- `adapters/ipfs/mocks/mock_geojsons.json`

Responsibilities:

- Validate `cell_id` format.
- Download project GeoJSON from Pinata/IPFS.
- Enforce max response size.
- Parse and validate JSON root shape.

Local/test behavior:

- If `ENVIRONMENT` is `local` or `test` and `PINATA_JWT` is empty, the app uses `MockIPFSService`.

## Satellite imagery adapter

File:

- `adapters/satellite/provider.py`

Implementations:

- `MockSatelliteImageryProvider`: deterministic local/test provider.
- `HTTPSatelliteImageryProvider`: HTTP adapter for external satellite providers.

Expected satellite observation shape:

```json
{
  "nir": 0.72,
  "red": 0.16,
  "blue": 0.08,
  "swir": 0.20,
  "timestamp": "2026-07-15T00:00:00Z",
  "cloud_coverage": 0.12
}
```

## Groq AI / LLM adapter

File:

- `adapters/ai/groq_provider.py`

Production AI analysis uses Groq's OpenAI-compatible chat completions API:

- Base URL: `https://api.groq.com/openai/v1`
- Chat path: `/chat/completions`
- Default model: `llama-3.1-8b-instant`

The provider receives score context, indicators, previous-score metadata, trends, and fraud flags.

It must return JSON compatible with:

```json
{
  "criticality": "low|medium|high",
  "description": "summary and recommendation"
}
```

There is no production mock AI provider. Tests patch the provider from `tests/conftest.py` to avoid external network calls.
