from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from models.schemas import ProjectGeometry, SatelliteObservation


class SatelliteImageryProvider(Protocol):
    """Boundary for satellite imagery providers."""

    async def get_observation(self, geometry: ProjectGeometry) -> SatelliteObservation:
        ...


@dataclass(frozen=True)
class MockSpectralProfile:
    nir: float
    red: float
    blue: float
    swir: float
    cloud_coverage: float


class MockSatelliteImageryProvider:
    """Deterministic satellite provider with multiple land-cover profiles.

    The provider reads the mock profile from GeoJSON properties, then applies a
    small deterministic geometry-based adjustment. This makes local results more
    realistic than a simple checksum while keeping tests reproducible.
    """

    _profiles: dict[str, MockSpectralProfile] = {
        "healthy_forest": MockSpectralProfile(nir=0.76, red=0.12, blue=0.06, swir=0.18, cloud_coverage=0.04),
        "early_reforestation": MockSpectralProfile(nir=0.48, red=0.24, blue=0.11, swir=0.30, cloud_coverage=0.10),
        "degraded_soil": MockSpectralProfile(nir=0.30, red=0.28, blue=0.16, swir=0.36, cloud_coverage=0.08),
        "burned_area": MockSpectralProfile(nir=0.18, red=0.22, blue=0.14, swir=0.52, cloud_coverage=0.06),
        "cloudy_vegetation": MockSpectralProfile(nir=0.54, red=0.20, blue=0.28, swir=0.26, cloud_coverage=0.48),
        "water_or_cloud": MockSpectralProfile(nir=0.06, red=0.08, blue=0.18, swir=0.04, cloud_coverage=0.70),
    }

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def get_observation(self, geometry: ProjectGeometry) -> SatelliteObservation:
        profile_name = self._extract_profile_name(geometry.geojson)
        profile = self._profiles.get(profile_name) or self._profile_from_cell_id(geometry.cell_id)
        adjustment = self._geometry_adjustment(geometry.geojson)

        return SatelliteObservation(
            nir=self._clamp(profile.nir + adjustment),
            red=self._clamp(profile.red - adjustment / 2),
            blue=self._clamp(profile.blue + abs(adjustment) / 3),
            swir=self._clamp(profile.swir - adjustment / 4),
            timestamp="2026-06-08T00:00:00Z",
            cloud_coverage=self._clamp(profile.cloud_coverage + abs(adjustment) / 2),
        )

    def _extract_profile_name(self, geojson: dict[str, Any]) -> str | None:
        if geojson.get("type") == "Feature":
            properties = geojson.get("properties") or {}
            if isinstance(properties, dict):
                value = properties.get("mock_satellite_profile")
                return value if isinstance(value, str) else None

        if geojson.get("type") == "FeatureCollection":
            features = geojson.get("features") or []
            if features and isinstance(features[0], dict):
                return self._extract_profile_name(features[0])

        return None

    def _profile_from_cell_id(self, cell_id: str) -> MockSpectralProfile:
        profile_names = sorted(self._profiles)
        checksum = sum(ord(char) for char in cell_id)
        return self._profiles[profile_names[checksum % len(profile_names)]]

    def _geometry_adjustment(self, geojson: dict[str, Any]) -> float:
        points = self._extract_points(geojson)
        if not points:
            return 0.0

        avg_lon = sum(lon for lon, _ in points) / len(points)
        avg_lat = sum(lat for _, lat in points) / len(points)
        lon_span = max(lon for lon, _ in points) - min(lon for lon, _ in points)
        lat_span = max(lat for _, lat in points) - min(lat for _, lat in points)

        # Small bounded signal based on latitude, longitude and approximate size.
        raw = (avg_lat * 0.0007) + (avg_lon * 0.0003) + ((lon_span + lat_span) * 0.2)
        return max(-0.025, min(0.025, raw))

    def _extract_points(self, geojson: dict[str, Any]) -> list[tuple[float, float]]:
        geometry_type = geojson.get("type")
        if geometry_type == "Feature":
            geometry = geojson.get("geometry")
            return self._extract_points(geometry) if isinstance(geometry, dict) else []
        if geometry_type == "FeatureCollection":
            points: list[tuple[float, float]] = []
            for feature in geojson.get("features") or []:
                if isinstance(feature, dict):
                    points.extend(self._extract_points(feature))
            return points
        return self._walk_coordinates(geojson.get("coordinates"))

    def _walk_coordinates(self, value: Any) -> list[tuple[float, float]]:
        if isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            return [(float(value[0]), float(value[1]))]
        if not isinstance(value, list):
            return []

        points: list[tuple[float, float]] = []
        for item in value:
            points.extend(self._walk_coordinates(item))
        return points

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)
