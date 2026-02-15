"""Pydantic models for SMHI API response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class ValidationResult(BaseModel):
    """Result of a validation check."""

    valid: bool
    severity: ValidationSeverity
    message: str
    field: str | None = None
    value: float | str | None = None


class ObservationValue(BaseModel):
    """A single observation value from the API."""

    date: int = Field(..., description="Unix timestamp in milliseconds")
    value: str = Field(..., description="Observed value as string")
    quality: str = Field(default="G", description="Quality flag")

    @field_validator("value")
    @classmethod
    def validate_value_is_numeric(cls, v: str) -> str:
        """Ensure value can be parsed as a number."""
        try:
            float(v)
        except ValueError as e:
            raise ValueError(f"Value '{v}' is not a valid number") from e
        return v


class StationMetadata(BaseModel):
    """Station metadata from API response."""

    key: int = Field(..., description="Station ID")
    name: str = Field(..., description="Station name")
    owner: str = Field(default="", description="Station owner")
    ownerCategory: str = Field(default="", description="Owner category")
    height: float = Field(default=0.0, description="Station height in meters")


class ParameterMetadata(BaseModel):
    """Parameter metadata from API response."""

    key: int = Field(..., description="Parameter ID")
    name: str = Field(..., description="Parameter name")
    summary: str = Field(default="", description="Parameter summary")
    unit: str = Field(default="", description="Measurement unit")


class PeriodMetadata(BaseModel):
    """Period metadata from API response."""

    key: str = Field(..., description="Period key")
    from_: int = Field(alias="from", description="Start timestamp")
    to: int = Field(..., description="End timestamp")
    summary: str = Field(default="", description="Period summary")


class MetObsResponse(BaseModel):
    """Full meteorological observation API response."""

    value: list[ObservationValue] = Field(default_factory=list)
    station: StationMetadata | None = None
    parameter: ParameterMetadata | None = None
    period: PeriodMetadata | None = None

    model_config = {"extra": "allow"}


class HydroObsResponse(BaseModel):
    """Full hydrological observation API response."""

    value: list[ObservationValue] = Field(default_factory=list)
    station: StationMetadata | None = None
    parameter: ParameterMetadata | None = None
    period: PeriodMetadata | None = None

    model_config = {"extra": "allow"}


class StationListItem(BaseModel):
    """Station item in station list response."""

    id: int
    name: str
    latitude: float = Field(default=0.0)
    longitude: float = Field(default=0.0)
    active: bool = Field(default=True)

    model_config = {"extra": "allow"}


def validate_observation_response(
    data: dict,
    response_type: str = "metobs",
) -> tuple[bool, list[ValidationResult]]:
    """Validate an observation API response against schema.

    Args:
        data: Raw API response dict
        response_type: Either 'metobs' or 'hydroobs'

    Returns:
        Tuple of (is_valid, list of validation results)
    """
    results: list[ValidationResult] = []
    model_class = MetObsResponse if response_type == "metobs" else HydroObsResponse

    try:
        model_class.model_validate(data)
        results.append(
            ValidationResult(
                valid=True,
                severity=ValidationSeverity.OK,
                message="Schema validation passed",
            )
        )
        return True, results

    except Exception as e:
        results.append(
            ValidationResult(
                valid=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Schema validation failed: {e}",
            )
        )
        return False, results


def validate_station_list(data: dict) -> tuple[bool, list[ValidationResult]]:
    """Validate a station list API response.

    Args:
        data: Raw API response dict

    Returns:
        Tuple of (is_valid, list of validation results)
    """
    results: list[ValidationResult] = []

    stations = data.get("station", [])
    if not isinstance(stations, list):
        results.append(
            ValidationResult(
                valid=False,
                severity=ValidationSeverity.CRITICAL,
                message="Expected 'station' to be a list",
                field="station",
            )
        )
        return False, results

    for i, station in enumerate(stations):
        try:
            StationListItem.model_validate(station)
        except Exception as e:
            results.append(
                ValidationResult(
                    valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Station {i} validation failed: {e}",
                    field=f"station[{i}]",
                )
            )

    if not results:
        results.append(
            ValidationResult(
                valid=True,
                severity=ValidationSeverity.OK,
                message=f"Validated {len(stations)} stations",
            )
        )

    all_valid = all(r.valid for r in results) if results else True
    return all_valid, results
