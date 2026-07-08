# Testing

Tests live in `tests/`.

## Run tests

```bash
PYTHONPATH=. pytest -q
```

## Test areas

- `tests/test_api.py`: API endpoint behavior and simplified response shape.
- `tests/test_indicators.py`: indicator formulas and numerical behavior.
- `tests/test_mock_services.py`: mock IPFS/satellite provider behavior.

## External AI calls in tests

Production uses Groq through `GroqAIProvider`. Tests do not call Groq. They patch the app AI provider with a test stub in `tests/conftest.py`, keeping the production code free of a mock AI provider while preserving deterministic test runs.

## Mock data

Mock files:

- `adapters/ipfs/mocks/mock_geojsons.json`
- `services/mocks/mock_satellite_profiles.json`

Known mock cell IDs include:

- `healthy-forest-cell`
- `early-reforestation-cell`
- `degraded-soil-cell`
- `burned-area-cell`
- `cloudy-cell`
