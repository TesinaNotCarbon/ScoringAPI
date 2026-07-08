# API

## Health check

### `GET /`

Returns service health and runtime metadata.

Example response:

```json
{
  "status": "ok",
  "service": "Scoring API",
  "version": "1.0.0",
  "environment": "local"
}
```

## Score by path parameter

### `GET /score/{cell_id}`

Optional query parameters:

- `previous_score`: integer from `0` to `100`.
- `measurement_date`: date in `YYYY-MM-DD` format.

Example:

```http
GET /score/healthy-forest-cell?previous_score=75&measurement_date=2026-07-15
```

Response:

```json
{
  "score": 82,
  "criticality": "low",
  "description": "Analysis summary and recommendation from the AI provider.",
  "measurement_date": "2026-07-15"
}
```

## Score by body

### `POST /score`

Request body:

```json
{
  "cell_id": "healthy-forest-cell",
  "previous_score": 75,
  "measurement_date": "2026-07-15"
}
```

Response uses the same simplified schema as `GET /score/{cell_id}`.

## Chainlink-compatible score endpoint

### `GET /chainlink/score/{cell_id}`

Returns the same compact response currently exposed by the scoring endpoint:

```json
{
  "score": 82,
  "criticality": "low",
  "description": "Analysis summary and recommendation from the AI provider.",
  "measurement_date": "2026-07-15"
}
```

## Error handling

- Invalid `cell_id`: `422`.
- IPFS, satellite provider, or AI provider failures: `502`.
