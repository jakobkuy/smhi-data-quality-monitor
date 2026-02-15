"""Configuration constants for SMHI Data Quality Monitor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    """Represents a monitoring station."""

    id: int
    name: str


# SMHI API base URLs
METOBS_BASE_URL = "https://opendata-download-metobs.smhi.se/api"
HYDROOBS_BASE_URL = "https://opendata-download-hydroobs.smhi.se/api"

# API configuration
API_VERSION = "1.0"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # exponential backoff multiplier

# Meteorological parameter IDs
PARAM_TEMPERATURE = 1      # Hourly air temperature (°C)
PARAM_WIND_SPEED = 4       # Hourly mean wind speed (m/s)
PARAM_HUMIDITY = 6         # Hourly relative humidity (%)
PARAM_PRECIPITATION = 7    # Daily precipitation (mm)

# Default meteorological stations (verified from SMHI API)
DEFAULT_STATIONS_METOBS: list[Station] = [
    Station(id=98210, name="Stockholm-Observatoriekullen"),
    Station(id=71420, name="Göteborg A"),
    Station(id=52350, name="Malmö A"),
    Station(id=162880, name="Luleå flygplats"),
    Station(id=134110, name="Östersund-Frösön"),
]

# Default hydrological stations
DEFAULT_STATIONS_HYDROOBS: list[Station] = [
    Station(id=2361, name="Stockholms ström"),
    Station(id=2251, name="Göta älv"),
]

# Physical range thresholds for validation
# Each parameter has: min (critical), max (critical), warn_min, warn_max
RANGE_THRESHOLDS: dict[str, dict[str, float]] = {
    "temperature": {
        "min": -60.0,
        "max": 55.0,
        "warn_min": -50.0,
        "warn_max": 40.0,
    },
    "wind_speed": {
        "min": 0.0,
        "max": 80.0,
        "warn_min": 0.0,
        "warn_max": 35.0,
    },
    "precipitation": {
        "min": 0.0,
        "max": 300.0,
        "warn_min": 0.0,
        "warn_max": 100.0,
    },
    "humidity": {
        "min": 0.0,
        "max": 100.0,
        "warn_min": 0.0,
        "warn_max": 100.0,
    },
    "water_level": {
        "min": -10.0,
        "max": 20.0,
        "warn_min": -5.0,
        "warn_max": 15.0,
    },
}

# Quality score weights (must sum to 1.0)
QUALITY_WEIGHTS: dict[str, float] = {
    "schema_validity": 0.20,
    "completeness": 0.30,
    "range_validity": 0.25,
    "anomaly_rate": 0.25,
}

# Anomaly detection settings
ZSCORE_THRESHOLD = 3.0  # Standard deviations from mean
IQR_MULTIPLIER = 1.5    # IQR multiplier for outlier detection
RATE_OF_CHANGE_THRESHOLD: dict[str, float] = {
    "temperature": 10.0,  # Max °C change per hour
    "wind_speed": 20.0,   # Max m/s change per hour
    "humidity": 30.0,     # Max % change per hour
}

# Completeness thresholds
MIN_COMPLETENESS_PERCENT = 90.0  # Minimum acceptable data completeness

# Period options for API requests
VALID_PERIODS = ["latest-hour", "latest-day", "latest-months", "corrected-archive"]
