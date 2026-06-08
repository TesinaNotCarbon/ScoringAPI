from __future__ import annotations

from typing import Any

from core.exceptions import InvalidGeoJSONError


def validate_geojson(geojson: dict[str, Any]) -> None:
    """Validate the minimum GeoJSON shape accepted by the scoring API."""
    if not isinstance(geojson, dict):
        raise InvalidGeoJSONError("GeoJSON must be an object")

    geometry_type = geojson.get("type")
    if geometry_type not in {"Polygon", "MultiPolygon", "Feature", "FeatureCollection"}:
        raise InvalidGeoJSONError("Unsupported GeoJSON type")

    if geometry_type in {"Polygon", "MultiPolygon"}:
        _validate_coordinates(geojson.get("coordinates"))
    elif geometry_type == "Feature":
        geometry = geojson.get("geometry")
        if not isinstance(geometry, dict):
            raise InvalidGeoJSONError("Feature must contain geometry")
        validate_geojson(geometry)
    else:
        features = geojson.get("features")
        if not isinstance(features, list) or not features:
            raise InvalidGeoJSONError("FeatureCollection must contain features")
        for feature in features:
            validate_geojson(feature)


def _validate_coordinates(coordinates: Any) -> None:
    if not isinstance(coordinates, list) or not coordinates:
        raise InvalidGeoJSONError("GeoJSON coordinates are required")
    _walk_coordinates(coordinates)


def _walk_coordinates(value: Any) -> None:
    if isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
        lon, lat = value
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise InvalidGeoJSONError("Coordinates are out of range")
        return
    if not isinstance(value, list) or not value:
        raise InvalidGeoJSONError("Invalid coordinates structure")
    for item in value:
        _walk_coordinates(item)
