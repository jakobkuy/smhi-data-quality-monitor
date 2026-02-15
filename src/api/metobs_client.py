"""Meteorological observations API client for SMHI."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.api.base_client import BaseClient
from src.utils.config import API_VERSION, METOBS_BASE_URL


@dataclass
class StationInfo:
    """Station metadata from the API."""

    id: int
    name: str
    latitude: float
    longitude: float
    active: bool


@dataclass
class Observation:
    """A single observation data point."""

    timestamp: datetime
    value: float
    quality: str


@dataclass
class ObservationSet:
    """Collection of observations for a station/parameter."""

    station_id: int
    station_name: str
    parameter_id: int
    parameter_name: str
    unit: str
    observations: list[Observation]


class MetObsClient(BaseClient):
    """Client for SMHI Meteorological Observations API.

    API structure: version → parameter → station → period → data
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the MetObs client."""
        super().__init__(base_url=METOBS_BASE_URL, **kwargs)

    def get_parameters(self) -> list[dict[str, Any]]:
        """Get list of available parameters.

        Returns:
            List of parameter metadata dicts
        """
        response = self.get(f"version/{API_VERSION}.json")
        return response.get("resource", [])

    def get_stations(self, parameter_id: int) -> list[StationInfo]:
        """Get stations that measure a specific parameter.

        Args:
            parameter_id: SMHI parameter ID (e.g., 1 for temperature)

        Returns:
            List of station information
        """
        response = self.get(
            f"version/{API_VERSION}/parameter/{parameter_id}.json"
        )

        stations = []
        for station_data in response.get("station", []):
            stations.append(
                StationInfo(
                    id=station_data["id"],
                    name=station_data["name"],
                    latitude=station_data.get("latitude", 0.0),
                    longitude=station_data.get("longitude", 0.0),
                    active=station_data.get("active", False),
                )
            )
        return stations

    def get_periods(self, parameter_id: int, station_id: int) -> list[str]:
        """Get available data periods for a station/parameter combination.

        Args:
            parameter_id: SMHI parameter ID
            station_id: Station ID

        Returns:
            List of available period keys
        """
        response = self.get(
            f"version/{API_VERSION}/parameter/{parameter_id}/station/{station_id}.json"
        )
        return [p["key"] for p in response.get("period", [])]

    def get_observations(
        self,
        parameter_id: int,
        station_id: int,
        period: str = "latest-months",
    ) -> ObservationSet:
        """Fetch observation data for a station/parameter.

        Args:
            parameter_id: SMHI parameter ID
            station_id: Station ID
            period: Time period (latest-hour, latest-day, latest-months, corrected-archive)

        Returns:
            ObservationSet with parsed observations
        """
        response = self.get(
            f"version/{API_VERSION}/parameter/{parameter_id}"
            f"/station/{station_id}/period/{period}/data.json"
        )

        observations = []
        for obs in response.get("value", []):
            timestamp = datetime.fromtimestamp(obs["date"] / 1000)
            observations.append(
                Observation(
                    timestamp=timestamp,
                    value=float(obs["value"]),
                    quality=obs.get("quality", "unknown"),
                )
            )

        station_info = response.get("station", {})
        parameter_info = response.get("parameter", {})

        return ObservationSet(
            station_id=station_info.get("key", station_id),
            station_name=station_info.get("name", "Unknown"),
            parameter_id=parameter_info.get("key", parameter_id),
            parameter_name=parameter_info.get("name", "Unknown"),
            unit=parameter_info.get("unit", ""),
            observations=observations,
        )

    def get_latest_observations(self, parameter_id: int) -> dict[int, Observation]:
        """Get the most recent observation from all stations for a parameter.

        Args:
            parameter_id: SMHI parameter ID

        Returns:
            Dict mapping station_id to latest observation
        """
        response = self.get(
            f"version/{API_VERSION}/parameter/{parameter_id}/station-set/all/period/latest-hour/data.json"
        )

        latest: dict[int, Observation] = {}
        for station_data in response.get("station", []):
            station_id = station_data["key"]
            values = station_data.get("value", [])
            if values:
                obs = values[-1]
                timestamp = datetime.fromtimestamp(obs["date"] / 1000)
                latest[station_id] = Observation(
                    timestamp=timestamp,
                    value=float(obs["value"]),
                    quality=obs.get("quality", "unknown"),
                )

        return latest
