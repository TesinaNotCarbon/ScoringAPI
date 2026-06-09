from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Protocol

from models.schemas import ProjectGeometry, SatelliteObservation

_MOCK_PROFILES_PATH = Path(__file__).with_name("mocks") / "mock_satellite_profiles.json"


class SatelliteImageryProvider(Protocol):
    """Boundary for satellite imagery providers."""

    async def get_observation(
        self,
        geometry: ProjectGeometry,
        measurement_date: str | None = None,
    ) -> SatelliteObservation:
        ...


@dataclass(frozen=True)
class MockSpectralProfile:
    nir: float
    red: float
    blue: float
    swir: float
    cloud_coverage: float


class MockSatelliteImageryProvider:
    """Deterministic satellite provider backed by editable mock files.

    IPFS mock data only contains cell id -> GeoJSON coordinates. The satellite
    profile mapping lives in ``services/mocks/mock_satellite_profiles.json`` so
    tests can use real-looking IPFS cell ids and modify scenarios without
    changing the coordinates stored in IPFS.
    """

    def __init__(self, profiles_path: Path = _MOCK_PROFILES_PATH) -> None:
        self.profiles_path = profiles_path
        self._profiles: dict[str, MockSpectralProfile] = {}
        self._cell_profiles: dict[str, str] = {}
        self._date_modifiers: dict[str, Any] = {}

    async def startup(self) -> None:
        self._load_profiles()

    async def shutdown(self) -> None:
        return None

    async def get_observation(
        self,
        geometry: ProjectGeometry,
        measurement_date: str | None = None,
    ) -> SatelliteObservation:
        if not self._profiles:
            self._load_profiles()

        profile = self._profile_for_cell_id(geometry.cell_id)
        adjustment = self._geometry_adjustment(geometry.geojson)
        date_adjustment = self._date_adjustment(measurement_date)

        return SatelliteObservation(
            nir=self._clamp(profile.nir + adjustment + date_adjustment.nir),
            red=self._clamp(profile.red - adjustment / 2 + date_adjustment.red),
            blue=self._clamp(profile.blue + abs(adjustment) / 3 + date_adjustment.blue),
            swir=self._clamp(profile.swir - adjustment / 4 + date_adjustment.swir),
            timestamp=f"{measurement_date or '2026-06-08'}T00:00:00Z",
            cloud_coverage=self._clamp(profile.cloud_coverage + abs(adjustment) / 2 + date_adjustment.cloud_coverage),
        )

    def _load_profiles(self) -> None:
        with self.profiles_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        profiles = data.get("profiles") or {}
        self._profiles = {
            name: MockSpectralProfile(**values)
            for name, values in profiles.items()
            if isinstance(values, dict)
        }
        self._cell_profiles = {
            cell_id: profile_name
            for cell_id, profile_name in (data.get("cell_profiles") or {}).items()
            if isinstance(cell_id, str) and isinstance(profile_name, str)
        }
        self._date_modifiers = data.get("date_modifiers") or {}

        if not self._profiles:
            raise ValueError("mock_satellite_profiles.json must define at least one profile")

    def _profile_for_cell_id(self, cell_id: str) -> MockSpectralProfile:
        configured_profile = self._cell_profiles.get(cell_id)
        if configured_profile in self._profiles:
            return self._profiles[configured_profile]

        profile_names = sorted(self._profiles)
        checksum = sum(ord(char) for char in cell_id)
        return self._profiles[profile_names[checksum % len(profile_names)]]

    def _date_adjustment(self, measurement_date: str | None) -> MockSpectralProfile:
        if not measurement_date:
            return MockSpectralProfile(0, 0, 0, 0, 0)

        try:
            month = date.fromisoformat(measurement_date).month
        except ValueError:
            return MockSpectralProfile(0, 0, 0, 0, 0)

        dry_months = set(self._date_modifiers.get("dry_season_months") or [])
        wet_months = set(self._date_modifiers.get("wet_season_months") or [])

        if month in dry_months:
            values = self._date_modifiers.get("dry_season") or {}
        elif month in wet_months:
            values = self._date_modifiers.get("wet_season") or {}
        else:
            values = {}

        return MockSpectralProfile(
            nir=float(values.get("nir", 0)),
            red=float(values.get("red", 0)),
            blue=float(values.get("blue", 0)),
            swir=float(values.get("swir", 0)),
            cloud_coverage=float(values.get("cloud_coverage", 0)),
        )

    def _geometry_adjustment(self, geojson: dict[str, Any]) -> float:
        points = self._extract_points(geojson)
        if not points:
            return 0.0

        avg_lon = sum(lon for lon, _ in points) / len(points)
        avg_lat = sum(lat for _, lat in points) / len(points)
        lon_span = max(lon for lon, _ in points) - min(lon for lon, _ in points)
        lat_span = max(lat for _, lat in points) - min(lat for _, lat in points)

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
