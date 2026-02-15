"""Tests for schema validation."""

import pytest

from src.validation.schema_validator import (
    MetObsResponse,
    ObservationValue,
    ValidationSeverity,
    validate_observation_response,
    validate_station_list,
)


class TestObservationValue:
    """Tests for ObservationValue model."""

    def test_valid_observation(self) -> None:
        """Valid observation parses correctly."""
        obs = ObservationValue(date=1704067200000, value="5.2", quality="G")
        assert obs.date == 1704067200000
        assert obs.value == "5.2"
        assert obs.quality == "G"

    def test_observation_with_negative_value(self) -> None:
        """Negative values are valid."""
        obs = ObservationValue(date=1704067200000, value="-10.5", quality="G")
        assert obs.value == "-10.5"

    def test_observation_with_non_numeric_value_raises(self) -> None:
        """Non-numeric value raises validation error."""
        with pytest.raises(ValueError):
            ObservationValue(date=1704067200000, value="invalid", quality="G")


class TestMetObsResponse:
    """Tests for MetObsResponse model."""

    def test_valid_response_parses(
        self, sample_valid_metobs_response: dict
    ) -> None:
        """Valid response parses without error."""
        response = MetObsResponse.model_validate(sample_valid_metobs_response)
        assert len(response.value) == 3
        assert response.station is not None
        assert response.station.key == 98210

    def test_response_with_extra_fields_allowed(self) -> None:
        """Extra fields are allowed (lenient validation)."""
        data = {
            "value": [],
            "unknown_field": "should be ignored",
        }
        response = MetObsResponse.model_validate(data)
        assert response.value == []

    def test_empty_response_valid(self) -> None:
        """Empty response with no values is valid."""
        data = {"value": []}
        response = MetObsResponse.model_validate(data)
        assert len(response.value) == 0


class TestValidateObservationResponse:
    """Tests for validate_observation_response function."""

    def test_valid_response_returns_true(
        self, sample_valid_metobs_response: dict
    ) -> None:
        """Valid response returns True with OK severity."""
        is_valid, results = validate_observation_response(
            sample_valid_metobs_response, "metobs"
        )
        assert is_valid is True
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.OK

    def test_invalid_response_returns_false(
        self, sample_invalid_metobs_response: dict
    ) -> None:
        """Invalid response returns False with CRITICAL severity."""
        is_valid, results = validate_observation_response(
            sample_invalid_metobs_response, "metobs"
        )
        assert is_valid is False
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.CRITICAL


class TestValidateStationList:
    """Tests for validate_station_list function."""

    def test_valid_station_list(self, sample_station_list_response: dict) -> None:
        """Valid station list validates successfully."""
        is_valid, results = validate_station_list(sample_station_list_response)
        assert is_valid is True
        assert results[0].message == "Validated 2 stations"

    def test_station_list_not_a_list_fails(self) -> None:
        """Station field that isn't a list fails validation."""
        data = {"station": "not a list"}
        is_valid, results = validate_station_list(data)
        assert is_valid is False
        assert results[0].severity == ValidationSeverity.CRITICAL

    def test_empty_station_list_valid(self) -> None:
        """Empty station list is valid."""
        data = {"station": []}
        is_valid, results = validate_station_list(data)
        assert is_valid is True
