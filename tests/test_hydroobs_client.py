"""Tests for HydroObs API client."""

import pytest
import responses

from src.api.hydroobs_client import HydroObsClient
from src.utils.config import HYDROOBS_BASE_URL


@pytest.fixture
def mock_hydro_stations_response() -> dict:
    """Mock hydrological station list response."""
    return {
        "station": [
            {
                "id": 2361,
                "name": "Stockholms ström",
                "latitude": 59.33,
                "longitude": 18.07,
                "active": True,
            }
        ]
    }


@pytest.fixture
def mock_hydro_observations_response() -> dict:
    """Mock hydrological observations response."""
    return {
        "value": [
            {"date": 1704067200000, "value": "1.25", "quality": "G"},
            {"date": 1704070800000, "value": "1.30", "quality": "G"},
        ],
        "station": {"key": 2361, "name": "Stockholms ström"},
        "parameter": {"key": 1, "name": "Water Level", "unit": "m"},
    }


class TestHydroObsClient:
    """Tests for HydroObsClient."""

    @responses.activate
    def test_get_stations_success(
        self, mock_hydro_stations_response: dict
    ) -> None:
        """Successfully fetches hydrological stations."""
        responses.add(
            responses.GET,
            f"{HYDROOBS_BASE_URL}/version/1.0/parameter/1.json",
            json=mock_hydro_stations_response,
            status=200,
        )

        client = HydroObsClient()
        stations = client.get_stations(parameter_id=1)

        assert len(stations) == 1
        assert stations[0].id == 2361
        assert stations[0].name == "Stockholms ström"

    @responses.activate
    def test_get_observations_success(
        self, mock_hydro_observations_response: dict
    ) -> None:
        """Successfully fetches hydrological observations."""
        responses.add(
            responses.GET,
            f"{HYDROOBS_BASE_URL}/version/1.0/parameter/1/station/2361/period/latest-day/data.json",
            json=mock_hydro_observations_response,
            status=200,
        )

        client = HydroObsClient()
        result = client.get_observations(
            parameter_id=1,
            station_id=2361,
            period="latest-day",
        )

        assert result.station_id == 2361
        assert len(result.observations) == 2
        assert result.observations[0].value == 1.25
        assert result.unit == "m"

    @responses.activate
    def test_get_parameters(self) -> None:
        """Fetches available parameters."""
        mock_response = {
            "resource": [
                {"key": "1", "title": "Water Level"},
                {"key": "2", "title": "Water Flow"},
            ]
        }
        responses.add(
            responses.GET,
            f"{HYDROOBS_BASE_URL}/version/1.0.json",
            json=mock_response,
            status=200,
        )

        client = HydroObsClient()
        params = client.get_parameters()

        assert len(params) == 2

    @responses.activate
    def test_uses_correct_base_url(
        self, mock_hydro_stations_response: dict
    ) -> None:
        """Uses hydrological API base URL, not meteorological."""
        responses.add(
            responses.GET,
            f"{HYDROOBS_BASE_URL}/version/1.0/parameter/1.json",
            json=mock_hydro_stations_response,
            status=200,
        )

        client = HydroObsClient()
        client.get_stations(parameter_id=1)

        # Verify the correct URL was called
        assert HYDROOBS_BASE_URL in responses.calls[0].request.url
        assert "metobs" not in responses.calls[0].request.url
