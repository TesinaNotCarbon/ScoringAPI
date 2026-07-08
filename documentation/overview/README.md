# Overview

The Scoring API is a FastAPI service that calculates an environmental score for a project cell and delegates fraud-risk analysis to an AI/LLM provider.

## Main functionality

Given a `cell_id`, the API:

1. Resolves project geometry from IPFS or a local mock.
2. Fetches satellite spectral observations for that geometry.
3. Calculates vegetation/burn indicators: NDVI, SAVI, EVI, and NBR.
4. Builds simple fraud-prevention flags and score trends.
5. Calculates a deterministic numeric score from the indicators.
6. Sends score, indicators, previous score metadata, trends, and flags to an AI provider.
7. Returns a simplified response:
   - `score`
   - `criticality`
   - `description`
   - `measurement_date`

## Project structure

```text
adapters/   external clients and infrastructure boundaries
api/        FastAPI routes
core/       app factory, config, logging, exceptions
models/     Pydantic schemas
services/   business logic, indicators, and scoring use cases
tests/      unit and API tests
main.py     ASGI entrypoint
```

## Request flow

```text
HTTP request
  -> api/routes.py
  -> services/scoring_service.py
  -> IPFS adapter
  -> Satellite adapter
  -> Indicator calculation
  -> Fraud flag calculation
  -> AI/LLM adapter
  -> simplified API response
```
