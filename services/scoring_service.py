from __future__ import annotations

from core.config import Settings
from models.schemas import Indicators, ScoreResponse, ScoreStatus
from services.fraud_prevention_service import FraudPreventionService
from services.indicators import calculate_indicators
from services.ipfs_service import IPFSService
from services.satellite_provider import SatelliteImageryProvider


class ScoringService:
    """Application use case for scoring a project cell."""

    def __init__(
        self,
        settings: Settings,
        ipfs_service: IPFSService,
        satellite_provider: SatelliteImageryProvider,
    ) -> None:
        self.settings = settings
        self.ipfs_service = ipfs_service
        self.satellite_provider = satellite_provider
        self.fraud_prevention_service = FraudPreventionService(settings)

    async def score_cell(
        self,
        cell_id: str,
        previous_score: int | None = None,
        measurement_date: str | None = None,
    ) -> ScoreResponse:
        geometry = await self.ipfs_service.download_geojson(cell_id)
        observation = await self.satellite_provider.get_observation(geometry, measurement_date)
        indicators = calculate_indicators(observation)
        flags = self._build_flags(indicators, observation.cloud_coverage)
        score = self._calculate_score(indicators, flags)

        comparison = self.fraud_prevention_service.compare_scores(score, previous_score)
        flags.extend(flag for flag in comparison.flags if flag not in flags)
        status = self._status_for(score, flags)
        review_required = status == ScoreStatus.REVIEW or comparison.review_required

        return ScoreResponse(
            cell_id=cell_id,
            score=score,
            previous_score=comparison.previous_score,
            score_delta=comparison.score_delta,
            score_trend=comparison.trend,
            measurement_date=measurement_date,
            status=status,
            indicators=indicators,
            flags=flags,
            review_required=review_required,
        )

    def _calculate_score(self, indicators: Indicators, flags: list[str]) -> int:
        ndvi_score = self._normalize(indicators.ndvi)
        savi_score = self._normalize(indicators.savi)
        evi_score = self._normalize(indicators.evi)
        nbr_score = self._normalize(indicators.nbr)

        weighted = ndvi_score * 0.35 + savi_score * 0.25 + evi_score * 0.25 + nbr_score * 0.15
        penalty = self._calculate_penalty(flags)
        return max(0, min(100, round(weighted - penalty)))

    def _calculate_penalty(self, flags: list[str]) -> int:
        penalties = {
            "high_cloud_coverage": 10,
            "possible_burn_or_logging": 25,
            "low_vegetation": 15,
            "indicator_mismatch": 10,
            "score_regression": 0,
            "suspicious_score_improvement": 0,
        }
        return sum(penalties.get(flag, 0) for flag in flags)

    def _build_flags(self, indicators: Indicators, cloud_coverage: float) -> list[str]:
        flags: list[str] = []
        if cloud_coverage > 0.30:
            flags.append("high_cloud_coverage")
        if indicators.ndvi < 0.20:
            flags.append("low_vegetation")
        if indicators.nbr < 0:
            flags.append("possible_burn_or_logging")
        if abs(indicators.ndvi - indicators.evi) > 0.35:
            flags.append("indicator_mismatch")
        return flags

    def _status_for(self, score: int, flags: list[str]) -> ScoreStatus:
        if "possible_burn_or_logging" in flags or score < self.settings.review_threshold:
            return ScoreStatus.REJECTED
        if flags or score < self.settings.approve_threshold:
            return ScoreStatus.REVIEW
        return ScoreStatus.APPROVED

    def _normalize(self, value: float) -> float:
        return max(0.0, min(100.0, (value + 1) * 50))
