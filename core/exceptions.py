class ScoringAPIError(Exception):
    """Base class for expected application errors."""


class InvalidCellIdError(ScoringAPIError):
    """Raised when a cell id is malformed."""


class InvalidGeoJSONError(ScoringAPIError):
    """Raised when downloaded geometry is invalid."""


class IPFSDownloadError(ScoringAPIError):
    """Raised when a GeoJSON document cannot be downloaded from IPFS."""


class SatelliteDataError(ScoringAPIError):
    """Raised when satellite data is unavailable or invalid."""
