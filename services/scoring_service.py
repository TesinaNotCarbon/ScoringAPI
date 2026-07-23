from __future__ import annotations

from datetime import datetime, timezone

from adapters.ai import AIProvider
from adapters.blockchain import ProjectManagerClient
from adapters.ipfs import IPFSService
from adapters.satellite import SatelliteImageryProvider
from core.config import Settings
from models.schemas import ChainlinkScoreResponse, Indicators, ProjectScoringAnalysisRequest, ScoreResponse
from services.indicators import calculate_indicators


class ScoringService:
    """Application use case for scoring a project through ProjectManager data."""

    def __init__(
        self,
        settings: Settings,
        ipfs_service: IPFSService,
        satellite_provider: SatelliteImageryProvider,
        ai_provider: AIProvider,
        project_manager: ProjectManagerClient,
    ) -> None:
        self.settings = settings
        self.ipfs_service = ipfs_service
        self.satellite_provider = satellite_provider
        self.ai_provider = ai_provider
        self.project_manager = project_manager

    async def score_project(self, project_id: str) -> ScoreResponse:
        cell_id = await self.project_manager.get_project_cell_id(project_id)
        previous_history = await self.project_manager.get_project_scoring_history(project_id)

        geometry = await self.ipfs_service.download_geojson(cell_id)
        observation = await self.satellite_provider.get_observation(geometry)
        indicators = calculate_indicators(observation)
        flags = self._build_flags(indicators, observation.cloud_coverage)
        measurement_date = self._measurement_date_from_timestamp(observation.timestamp)

        analysis = await self.ai_provider.analyze_project_scoring(
            ProjectScoringAnalysisRequest(
                project_id=project_id,
                cell_id=cell_id,
                measurement_date=measurement_date,
                indicators=indicators,
                cloud_coverage=observation.cloud_coverage,
                flags=flags,
                previous_scoring_history=previous_history,
            )
        )

        return ScoreResponse(
            project_id=project_id,
            cell_id=cell_id,
            scoring=analysis.scoring,
            fraud_scoring=analysis.fraud_scoring,
            measurement_date=measurement_date,
        )

    async def score_project_for_consensus(self, project_id: str) -> ChainlinkScoreResponse:
        response = await self.score_project(project_id)
        return ChainlinkScoreResponse(
            project_id=response.project_id,
            cell_id=response.cell_id,
            scoring=self._scale_score(response.scoring),
            fraud_scoring=self._scale_score(response.fraud_scoring),
            measurement_date=response.measurement_date,
        )

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

    def _measurement_date_from_timestamp(self, timestamp: str) -> int:
        normalized = timestamp.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return int(datetime.now(tz=timezone.utc).timestamp())
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())

    def _scale_score(self, score: str) -> int:
        return int(round(float(score) * 100))
