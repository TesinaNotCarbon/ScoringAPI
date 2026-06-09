import pytest

from core.config import Settings
from services.indicators import calculate_indicators
from services.mock_ipfs_service import MockIPFSService
from services.satellite_provider import MockSatelliteImageryProvider


@pytest.mark.asyncio
async def test_mock_ipfs_loads_known_geojson() -> None:
    service = MockIPFSService(Settings(environment="test"))
    await service.startup()

    geometry = await service.download_geojson("healthy-forest-cell")

    assert geometry.geojson["type"] == "Polygon"
    assert "coordinates" in geometry.geojson


@pytest.mark.asyncio
async def test_mock_satellite_provider_uses_geojson_profile() -> None:
    ipfs = MockIPFSService(Settings(environment="test"))
    provider = MockSatelliteImageryProvider()
    await ipfs.startup()

    healthy_geometry = await ipfs.download_geojson("healthy-forest-cell")
    burned_geometry = await ipfs.download_geojson("burned-area-cell")

    healthy = calculate_indicators(await provider.get_observation(healthy_geometry))
    burned = calculate_indicators(await provider.get_observation(burned_geometry))

    assert healthy.ndvi > 0.65
    assert healthy.nbr > 0.50
    assert burned.ndvi < 0
    assert burned.nbr < 0


@pytest.mark.asyncio
async def test_mock_satellite_provider_changes_with_measurement_date() -> None:
    ipfs = MockIPFSService(Settings(environment="test"))
    provider = MockSatelliteImageryProvider()
    await ipfs.startup()

    geometry = await ipfs.download_geojson("healthy-forest-cell")
    dry = await provider.get_observation(geometry, "2026-07-15")
    wet = await provider.get_observation(geometry, "2026-01-15")

    assert dry.timestamp == "2026-07-15T00:00:00Z"
    assert wet.timestamp == "2026-01-15T00:00:00Z"
    assert dry.nir < wet.nir


@pytest.mark.asyncio
async def test_unknown_cell_id_maps_to_deterministic_geojson() -> None:
    service = MockIPFSService(Settings(environment="test"))
    await service.startup()

    first = await service.download_geojson("unknown-cell-123")
    second = await service.download_geojson("unknown-cell-123")

    assert first.geojson == second.geojson
