# Configuration

Configuration is managed with Pydantic settings in `core/config.py` and environment variables.

See `.env.example` for the full list.

## App settings

- `APP_NAME`
- `APP_VERSION`
- `ENVIRONMENT`: `local`, `test`, `staging`, or `production`.
- `DEBUG`
- `HOST`
- `PORT`
- `LOG_LEVEL`
- `CORS_ORIGINS`

## IPFS / Pinata

- `PINATA_GATEWAY_BASE_URL`
- `PINATA_JWT`
- `IPFS_TIMEOUT_SECONDS`
- `IPFS_MAX_BYTES`
- `MAX_CONCURRENT_DOWNLOADS`

If `PINATA_JWT` is empty in `local` or `test`, the app uses `adapters/ipfs/mocks/MockIPFSService`.

## Satellite provider

- `SATELLITE_PROVIDER`: `mock` or `http`.
- `SATELLITE_PROVIDER_BASE_URL`
- `SATELLITE_PROVIDER_OBSERVATION_PATH`
- `SATELLITE_PROVIDER_API_KEY`
- `SATELLITE_TIMEOUT_SECONDS`

Use `mock` for local development and tests. Use `http` to call an external satellite provider.

## Groq AI / LLM provider

- `GROQ_BASE_URL`: defaults to `https://api.groq.com/openai/v1`.
- `GROQ_CHAT_PATH`: defaults to `/chat/completions`.
- `GROQ_API_KEY`: required to run the app against Groq.
- `GROQ_MODEL`: defaults to `llama-3.1-8b-instant`.
- `GROQ_TIMEOUT_SECONDS`: request timeout.

Groq has an OpenAI-compatible API. Create a key in GroqCloud and set `GROQ_API_KEY` in your environment.

## Scoring thresholds

- `APPROVE_THRESHOLD`
- `REVIEW_THRESHOLD`
- `DRASTIC_IMPROVEMENT_THRESHOLD`

Approval/rejection status is no longer returned by the API, but thresholds are still used internally for score penalties and fraud-analysis context.
