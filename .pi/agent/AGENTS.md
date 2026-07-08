# Agents.md

## Application Context

This application is a scoring API for reforestation and environmental verification projects. It will be invoked by a Chainlink oracle, using Chainlink Functions or the Chainlink Runtime Environment (CRE), so it must expose simple, deterministic, secure HTTP endpoints with responses that are easy to consume on-chain.

The main API input is a `cell_id`. This `cell_id` identifies the coordinates or polygon of the project stored on IPFS through Pinata. The API must download the GeoJSON associated with the `cell_id`, query satellite imagery data from a mocked external source, calculate environmental indicators, and produce a final score.

The goal is to evaluate whether the reported area actually corresponds to a valid project, detect signs of vegetation, reforestation, degradation, fire, logging, or potential fraud, and return a result suitable for smart contract consumption.

## Expected Functional Flow

1. Receive a `cell_id` in the scoring endpoint.
2. Download the GeoJSON or coordinate metadata associated with the `cell_id` from IPFS/Pinata.
3. Validate the format, size, and geographic consistency of the area.
4. Query a mocked satellite imagery interface.
5. Obtain the required bands or metrics: `NIR`, `Red`, `Blue`, `SWIR`, timestamps, and quality metadata.
6. Calculate environmental indicators.
7. Evaluate anti-fraud and historical consistency rules.
8. Calculate a final score.
9. Return a stable JSON response for Chainlink consumption.

## IPFS / Pinata Integration

The service must be abstracted behind a dedicated interface or class, for example `IPFSService`.

Expected best practices:

- Use an async HTTP client, such as `aiohttp` or `httpx.AsyncClient`.
- Handle timeouts.
- Limit concurrency with semaphores if multiple CIDs are downloaded.
- Retry on `429 Too Many Requests` while respecting `Retry-After`.
- Validate `Content-Type` when applicable.
- Do not expose Pinata tokens in logs or responses.
- Configure credentials through environment variables.

The suggested pattern is similar to:

```python
class IPFSService:
    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def download_geojson(self, cell_id: str) -> dict: ...
```

## Satellite Sources

Initially, a mocked API should be used behind interfaces to avoid coupling domain logic to a specific provider.

Possible real providers in the future:

- Google Earth Engine (GEE), including Landsat and Sentinel.
- NASA Earthdata / USGS.
- Sentinel-2 / EOS Landviewer.

The domain layer must not depend directly on these providers. Define an abstraction, for example:

```python
class SatelliteImageryProvider(Protocol):
    async def get_observation(self, geometry: dict) -> SatelliteObservation: ...
```

The mock implementation must support deterministic tests.

## Environmental Indicators

### NDVI

Estimates the amount, quality, and development of vegetation.

Formula:

```text
NDVI = (NIR - Red) / (NIR + Red)
```

Use:

- Confirm whether the area has existing vegetation.
- Differentiate healthy vegetation, sparse vegetation, bare soil, water, snow, or clouds.

Interpretation:

- `0.66 – 1`: healthy and dense vegetation.
- `0.33 – 0.66`: stressed or sparse vegetation.
- Close to `0`: little vegetation, early-stage crops, bare soil, or non-productive area.
- Negative: water, snow, clouds, or other non-vegetated surfaces.

Limitations:

- It saturates in very dense forests.
- It can be affected by soil brightness in early reforestation stages.

### SAVI

Corrects soil noise, especially useful in projects with seedlings or sparse vegetation.

Formula:

```text
SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
```

Recommended default value for `L`: `0.5`.

Notes:

- If vegetation is very sparse, `L` approaches `1`.
- If vegetation is very dense, `L` approaches `0`, behaving similarly to NDVI.

### EVI

Uses the blue band to correct atmospheric distortions such as aerosols or smoke.

Formula:

```text
EVI = G * (NIR - Red) / (NIR + C1 * Red - C2 * Blue + L)
```

Typical values:

- `G = 2.5`
- `C1 = 6`
- `C2 = 7.5`
- `L = 1`

Advantage:

- It does not saturate as quickly as NDVI.
- It is more sensitive in high-biomass areas.

### NBR

Normalized Burn Ratio. Detects fires, logging, or severe degradation.

Formula:

```text
NBR = (NIR - SWIR) / (NIR + SWIR)
```

Use:

- Healthy vegetation reflects a lot of `NIR`.
- Burned or logged vegetation reflects more `SWIR`.
- A sharp drop in NBR must trigger an alert for possible fraud, disaster event, or reversal.

## Final Scoring

The final score must be calculated from normalized indicators and explicit business rules.

Recommendations:

- Separate indicator calculation from scoring calculation.
- Keep weights configurable.
- Include reasons or flags in the response for auditability.
- Avoid hidden or hardcoded logic inside FastAPI controllers.
- Keep the output deterministic for the same input and the same satellite data.

Example response:

```json
{
  "cell_id": "bafy...",
  "score": 82,
  "status": "approved",
  "indicators": {
    "ndvi": 0.71,
    "savi": 0.62,
    "evi": 0.68,
    "nbr": 0.55
  },
  "flags": [],
  "review_required": false
}
```

Suggested statuses:

- `approved`: sufficient score and no critical flags.
- `review`: requires manual review due to inconsistencies, significant differences between indicators, or ambiguous signals.
- `rejected`: low score, invalid area, or strong fraud signals.

## Fraud Detection and Consistency

Expected rules:

- Avoid double counting: the indicated area must not overlap with projects already completed or in progress.
- Verify that the initial area does not correspond to consolidated forest if the project claims reforestation from degraded soil.
- Detect sharp NBR drops as possible fire, logging, or reversal.
- Set `review_required = true` when there are significant differences between the current score, historical score, or indicators.
- If no analysis is available for the project, consider a review state or operational freezing in consuming systems.
- Do not execute destructive on-chain decisions directly from this API; return clear flags so the contract/protocol can decide.

## Recommended FastAPI Architecture

Separate by layers:

```text
app/
  main.py
  api/
    routes/
      health.py
      scoring.py
    schemas/
      scoring.py
  core/
    config.py
    exceptions.py
    logging.py
    security.py
  domain/
    models.py
    indicators.py
    scoring.py
    fraud.py
  services/
    ipfs_service.py
    satellite_provider.py
    mock_satellite_provider.py
  repositories/
    project_repository.py
  tests/
```

Responsibilities:

- `api`: endpoints, HTTP validation, and serialization.
- `domain`: pure business logic, indicators, scoring, and fraud detection.
- `services`: integration with IPFS, Pinata, and satellite providers.
- `repositories`: access to internal storage if a database is added.
- `core`: configuration, errors, logging, and security.

## Development Guidelines

- Use FastAPI with async handlers when I/O is involved.
- Use Pydantic for request/response schemas.
- Keep controllers thin.
- Do not mix external HTTP access with scoring logic.
- Use interfaces/protocols for external providers.
- Write unit tests for the NDVI, SAVI, EVI, and NBR formulas.
- Write integration tests for the scoring endpoint using mock providers.
- Validate division by zero in all formulas.
- Normalize numeric outputs and define precision/rounding.
- Use environment variables for sensitive configuration.
- Do not log JWTs, private CIDs, full payloads, or sensitive coordinates unless necessary.
- Document scoring decisions and thresholds.

## Security

- Validate the `cell_id` format and reject excessively long inputs.
- Apply timeouts to external calls.
- Limit the size of documents downloaded from IPFS.
- Validate GeoJSON structure and coordinates.
- Prevent SSRF: build URLs only against the allowed Pinata gateway.
- Use rate limiting if the API becomes public.
- Add authentication if the endpoint should not be public.
- Handle errors with safe messages, without leaking secrets.
- Consider replay/idempotency for oracle invocations.

## Chainlink Compatibility

- Keep responses compact and deterministic.
- Avoid deeply nested responses if they will be consumed on-chain.
- Define clear error codes.
- Recommended endpoint: `GET /score/{cell_id}` or `POST /score`.
- If Chainlink Functions only requires the score, consider a simplified endpoint returning `{ "score": number }`.
- Keep the full endpoint for off-chain auditability.

## Initial Acceptance Criteria

- A health check endpoint exists.
- A scoring endpoint exists and receives a `cell_id`.
- GeoJSON is downloaded from IPFS through an abstracted service.
- The mock satellite provider is queried through an interface.
- NDVI, SAVI, EVI, and NBR are calculated.
- The final score is calculated using explicit rules.
- Flags and review state are returned when applicable.
- Tests exist for indicators and basic scoring.
