"""Shared pytest fixtures for SMHI Data Quality Monitor tests."""

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def sample_valid_metobs_response() -> dict:
    """Sample valid meteorological observation response."""
    return {
        "value": [
            {"date": 1704067200000, "value": "5.2", "quality": "G"},
            {"date": 1704070800000, "value": "4.8", "quality": "G"},
            {"date": 1704074400000, "value": "4.5", "quality": "G"},
        ],
        "station": {
            "key": 98210,
            "name": "Stockholm-Observatoriekullen",
            "owner": "SMHI",
            "ownerCategory": "SMHI",
            "height": 43.0,
        },
        "parameter": {
            "key": 1,
            "name": "Lufttemperatur",
            "summary": "momentanvärde, 1 gång/tim",
            "unit": "degree celsius",
        },
        "period": {
            "key": "latest-day",
            "from": 1704067200000,
            "to": 1704153600000,
            "summary": "Data från senaste dygnet",
        },
    }


@pytest.fixture
def sample_invalid_metobs_response() -> dict:
    """Sample invalid response with missing required fields."""
    return {
        "value": [
            {"date": 1704067200000, "quality": "G"},  # Missing 'value' field
        ],
    }


@pytest.fixture
def sample_station_list_response() -> dict:
    """Sample station list API response."""
    return {
        "station": [
            {
                "id": 98210,
                "name": "Stockholm-Observatoriekullen",
                "latitude": 59.3417,
                "longitude": 18.0549,
                "active": True,
            },
            {
                "id": 71420,
                "name": "Göteborg A",
                "latitude": 57.7156,
                "longitude": 11.9924,
                "active": True,
            },
        ]
    }


@pytest.fixture
def temperature_values_normal() -> list[float]:
    """Normal temperature values for Sweden."""
    return [5.2, 5.5, 5.8, 6.0, 5.9, 5.7, 5.4, 5.1, 4.8, 4.5]


@pytest.fixture
def temperature_values_with_anomaly() -> list[float]:
    """Temperature values with an obvious spike anomaly."""
    return [5.2, 5.5, 5.8, 45.0, 5.9, 5.7, 5.4, 5.1, 4.8, 4.5]  # 45.0 is anomaly


@pytest.fixture
def temperature_values_with_critical_outlier() -> list[float]:
    """Temperature values with physically impossible value."""
    return [5.2, 5.5, 100.0, 6.0, 5.9]  # 100.0 exceeds max of 55


@pytest.fixture
def hourly_timestamps() -> list[datetime]:
    """Hourly timestamps for 10 observations."""
    base = datetime(2024, 1, 1, 0, 0)
    return [base + timedelta(hours=i) for i in range(10)]


@pytest.fixture
def timestamps_with_gap() -> list[datetime]:
    """Timestamps with a 3-hour gap."""
    base = datetime(2024, 1, 1, 0, 0)
    # 0, 1, 2, then gap, then 6, 7, 8, 9
    times = [base + timedelta(hours=i) for i in range(3)]
    times.extend([base + timedelta(hours=i) for i in range(6, 10)])
    return times


@pytest.fixture
def complete_timestamps() -> list[datetime]:
    """Complete hourly timestamps for 24 hours."""
    base = datetime(2024, 1, 1, 0, 0)
    return [base + timedelta(hours=i) for i in range(24)]
