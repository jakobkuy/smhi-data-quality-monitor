"""Hydrological observations API client for SMHI."""

from datetime import datetime
from typing import Any

from src.api.base_client import BaseClient
from src.api.metobs_client import Observation, ObservationSet, StationInfo
from src.utils.config import API_VERSION, HYDROOBS_BASE_URL


class HydroObsClient(BaseClient):
    """Client for SMHI Hydrological Observations API.

    Same traversal pattern as MetObs: version → parameter → station → period → data
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the HydroObs client."""
        super().__init__(base_url=HYDROOBS_BASE_URL, **kwargs)

    def get_parameters(self) -> list[dict[str, Any]]:
        """Get list of available hydrological parameters.

        Returns:
            List of parameter metadata dicts
        """
        response = self.get(f"version/{API_VERSION}.json")
        return response.get("resource", [])  # type: ignore[no-any-return]

    def get_stations(self, parameter_id: int) -> list[StationInfo]:
        """Get stations that measure a specific hydrological parameter.

        Args:
            parameter_id: SMHI parameter ID

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
            period: Time period

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
