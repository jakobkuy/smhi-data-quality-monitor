"""Tests for MetObs API client."""

import pytest
import responses

from src.api.base_client import APIError
from src.api.metobs_client import MetObsClient
from src.utils.config import METOBS_BASE_URL


@pytest.fixture
def mock_stations_response() -> dict:
    """Mock station list response."""
    return {
        "station": [
            {
                "id": 98210,
                "name": "Stockholm",
                "latitude": 59.34,
                "longitude": 18.05,
                "active": True,
            }
        ]
    }


@pytest.fixture
def mock_observations_response() -> dict:
    """Mock observations response."""
    return {
        "value": [
            {"date": 1704067200000, "value": "5.2", "quality": "G"},
            {"date": 1704070800000, "value": "5.5", "quality": "G"},
        ],
        "station": {"key": 98210, "name": "Stockholm"},
        "parameter": {"key": 1, "name": "Temperature", "unit": "celsius"},
    }


class TestMetObsClient:
    """Tests for MetObsClient."""

    @responses.activate
    def test_get_stations_success(self, mock_stations_response: dict) -> None:
        """Successfully fetches stations."""
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/1.json",
            json=mock_stations_response,
            status=200,
        )

        client = MetObsClient()
        stations = client.get_stations(parameter_id=1)

        assert len(stations) == 1
        assert stations[0].id == 98210
        assert stations[0].name == "Stockholm"

    @responses.activate
    def test_get_observations_success(
        self, mock_observations_response: dict
    ) -> None:
        """Successfully fetches observations."""
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/1/station/98210/period/latest-day/data.json",
            json=mock_observations_response,
            status=200,
        )

        client = MetObsClient()
        result = client.get_observations(
            parameter_id=1,
            station_id=98210,
            period="latest-day",
        )

        assert result.station_id == 98210
        assert len(result.observations) == 2
        assert result.observations[0].value == 5.2

    @responses.activate
    def test_handles_404_error(self) -> None:
        """404 error raises APIError."""
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/999.json",
            json={"error": "Not found"},
            status=404,
        )

        client = MetObsClient()
        with pytest.raises(APIError) as exc_info:
            client.get_stations(parameter_id=999)

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_retry_on_server_error(self) -> None:
        """Retries on 500 error then succeeds."""
        # First call fails
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/1.json",
            json={"error": "Server error"},
            status=500,
        )
        # Second call succeeds
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/1.json",
            json={"station": []},
            status=200,
        )

        client = MetObsClient(max_retries=1)
        stations = client.get_stations(parameter_id=1)

        assert len(responses.calls) == 2
        assert stations == []

    @responses.activate
    def test_context_manager(self, mock_stations_response: dict) -> None:
        """Works as context manager."""
        responses.add(
            responses.GET,
            f"{METOBS_BASE_URL}/version/1.0/parameter/1.json",
            json=mock_stations_response,
            status=200,
        )

        with MetObsClient() as client:
            stations = client.get_stations(parameter_id=1)
            assert len(stations) == 1
