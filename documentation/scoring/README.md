# Scoring and Fraud Analysis

## Indicator calculation

File:

- `services/indicators.py`

The service calculates four environmental indicators from satellite spectral bands:

- `NDVI`: vegetation health using `nir` and `red`.
- `SAVI`: vegetation adjusted for soil background.
- `EVI`: enhanced vegetation signal using `nir`, `red`, and `blue`.
- `NBR`: burn/logging signal using `nir` and `swir`.

## Score calculation

File:

- `services/scoring_service.py`

The score is deterministic and normalized to `0..100`.

Weighted formula:

- NDVI: `35%`
- SAVI: `25%`
- EVI: `25%`
- NBR: `15%`

Penalties are applied for simple satellite-derived flags.

## Fraud-prevention flags

Files:

- `services/scoring_service.py`
- `services/fraud_prevention_service.py`

Current flags include:

- `high_cloud_coverage`
- `possible_burn_or_logging`
- `low_vegetation`
- `indicator_mismatch`
- `score_regression`
- `suspicious_score_improvement`

The service no longer calculates final approval status. Instead, these indicators are sent to the AI provider.

## Score comparison and trends

If `previous_score` is provided, the fraud prevention service calculates:

- `score_delta`
- `score_trend`

Possible trends:

- `no_baseline`
- `regressed`
- `suspicious_improvement`
- `improved`
- `unchanged`

## AI fraud analysis

The AI adapter receives a structured payload with project scoring context and returns:

- `criticality`: `low`, `medium`, or `high`.
- `description`: summary/recommendation explaining the risk analysis.

This keeps the public API response simple while preserving useful internal analysis for the LLM.
