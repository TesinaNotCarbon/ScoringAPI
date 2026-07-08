from __future__ import annotations

from models.schemas import Indicators, SatelliteObservation

_EPSILON = 1e-12


def safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < _EPSILON:
        return 0.0
    return numerator / denominator


def round_indicator(value: float) -> float:
    return round(value, 4)


def calculate_ndvi(nir: float, red: float) -> float:
    return round_indicator(safe_ratio(nir - red, nir + red))


def calculate_savi(nir: float, red: float, soil_factor: float = 0.5) -> float:
    return round_indicator(safe_ratio(nir - red, nir + red + soil_factor) * (1 + soil_factor))


def calculate_evi(
    nir: float,
    red: float,
    blue: float,
    gain: float = 2.5,
    c1: float = 6.0,
    c2: float = 7.5,
    canopy_background: float = 1.0,
) -> float:
    denominator = nir + c1 * red - c2 * blue + canopy_background
    return round_indicator(gain * safe_ratio(nir - red, denominator))


def calculate_nbr(nir: float, swir: float) -> float:
    return round_indicator(safe_ratio(nir - swir, nir + swir))


def calculate_indicators(observation: SatelliteObservation) -> Indicators:
    return Indicators(
        ndvi=calculate_ndvi(observation.nir, observation.red),
        savi=calculate_savi(observation.nir, observation.red),
        evi=calculate_evi(observation.nir, observation.red, observation.blue),
        nbr=calculate_nbr(observation.nir, observation.swir),
    )
