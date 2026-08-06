from __future__ import annotations

import pytest

from core.config import Settings
from models.schemas import Indicators, SatelliteObservation
from services.fraud_prevention_service import FraudPreventionService
from services.scoring_service import ScoringService


class DummyScoringService(ScoringService):
    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        pass


def test_fraud_prevention_no_baseline() -> None:
    comparison = FraudPreventionService(Settings(environment="test")).compare_scores(70, None)

    assert comparison.previous_score is None
    assert comparison.current_score == 70
    assert comparison.score_delta is None
    assert comparison.trend == "no_baseline"
    assert comparison.flags == []
    assert comparison.review_required is False


@pytest.mark.parametrize(
    "current, previous, trend, flags, review_required",
    [
        (60, 70, "regressed", ["score_regression"], True),
        (95, 70, "suspicious_improvement", ["suspicious_score_improvement"], True),
        (80, 70, "improved", [], False),
        (70, 70, "unchanged", [], False),
    ],
)
def test_fraud_prevention_compares_scores(
    current: int, previous: int, trend: str, flags: list[str], review_required: bool
) -> None:
    comparison = FraudPreventionService(Settings(environment="test")).compare_scores(current, previous)

    assert comparison.score_delta == current - previous
    assert comparison.trend == trend
    assert comparison.flags == flags
    assert comparison.review_required is review_required


def test_scoring_service_builds_all_flags() -> None:
    service = DummyScoringService()
    indicators = Indicators(ndvi=0.10, savi=0.1, evi=0.60, nbr=-0.1)

    assert service._build_flags(indicators, 0.31) == [
        "high_cloud_coverage",
        "low_vegetation",
        "possible_burn_or_logging",
        "indicator_mismatch",
    ]


def test_scoring_service_measurement_date_parsing() -> None:
    service = DummyScoringService()

    assert service._measurement_date_from_timestamp("1970-01-01T00:00:01Z") == 1
    assert service._measurement_date_from_timestamp("1970-01-01T00:00:02") == 2
    assert isinstance(service._measurement_date_from_timestamp("not-a-date"), int)


def test_scoring_service_scale_score_rounds() -> None:
    service = DummyScoringService()

    assert service._scale_score("0.75") == 75
    assert service._scale_score("0.805") == 80


def test_calculate_indicators_integration() -> None:
    from services.indicators import calculate_indicators

    observation = SatelliteObservation(
        nir=0.72, red=0.16, blue=0.08, swir=0.22, timestamp="2026-01-01T00:00:00Z"
    )
    indicators = calculate_indicators(observation)

    assert indicators.ndvi == 0.6364
    assert indicators.savi == 0.6087
    assert indicators.evi == 0.6731
    assert indicators.nbr == 0.5319
