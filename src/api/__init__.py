"""SMHI API clients for meteorological and hydrological data."""

from src.api.base_client import APIError, BaseClient, RateLimitError
from src.api.hydroobs_client import HydroObsClient
from src.api.metobs_client import (
    MetObsClient,
    Observation,
    ObservationSet,
    StationInfo,
)

__all__ = [
    "APIError",
    "BaseClient",
    "RateLimitError",
    "MetObsClient",
    "HydroObsClient",
    "StationInfo",
    "Observation",
    "ObservationSet",
]
