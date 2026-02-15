"""Physics-based range validation for sensor data."""

from dataclasses import dataclass
from enum import Enum

from src.utils.config import RANGE_THRESHOLDS


class RangeSeverity(str, Enum):
    """Severity level for range check results."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RangeCheckResult:
    """Result of a range validation check."""

    value: float
    parameter: str
    severity: RangeSeverity
    message: str
    threshold_violated: str | None = None


def check_range(
    value: float,
    parameter: str,
    custom_thresholds: dict[str, float] | None = None,
) -> RangeCheckResult:
    """Check if a value falls within acceptable physical range.

    Args:
        value: The measured value
        parameter: Parameter type (temperature, wind_speed, etc.)
        custom_thresholds: Optional override thresholds

    Returns:
        RangeCheckResult with severity level
    """
    thresholds = custom_thresholds or RANGE_THRESHOLDS.get(parameter)

    if not thresholds:
        return RangeCheckResult(
            value=value,
            parameter=parameter,
            severity=RangeSeverity.OK,
            message=f"No thresholds defined for {parameter}",
        )

    min_val = thresholds.get("min", float("-inf"))
    max_val = thresholds.get("max", float("inf"))
    warn_min = thresholds.get("warn_min", min_val)
    warn_max = thresholds.get("warn_max", max_val)

    # Check critical range (physically impossible)
    if value < min_val:
        return RangeCheckResult(
            value=value,
            parameter=parameter,
            severity=RangeSeverity.CRITICAL,
            message=f"{parameter} value {value} is below minimum {min_val}",
            threshold_violated="min",
        )

    if value > max_val:
        return RangeCheckResult(
            value=value,
            parameter=parameter,
            severity=RangeSeverity.CRITICAL,
            message=f"{parameter} value {value} is above maximum {max_val}",
            threshold_violated="max",
        )

    # Check warning range (unusual but possible)
    if value < warn_min:
        return RangeCheckResult(
            value=value,
            parameter=parameter,
            severity=RangeSeverity.WARNING,
            message=f"{parameter} value {value} is unusually low (below {warn_min})",
            threshold_violated="warn_min",
        )

    if value > warn_max:
        return RangeCheckResult(
            value=value,
            parameter=parameter,
            severity=RangeSeverity.WARNING,
            message=f"{parameter} value {value} is unusually high (above {warn_max})",
            threshold_violated="warn_max",
        )

    return RangeCheckResult(
        value=value,
        parameter=parameter,
        severity=RangeSeverity.OK,
        message=f"{parameter} value {value} is within normal range",
    )


def validate_observations(
    values: list[float],
    parameter: str,
) -> tuple[list[RangeCheckResult], dict[str, int]]:
    """Validate a list of observations and summarize results.

    Args:
        values: List of measured values
        parameter: Parameter type

    Returns:
        Tuple of (list of results, summary counts by severity)
    """
    results = [check_range(v, parameter) for v in values]

    summary = {
        "ok": sum(1 for r in results if r.severity == RangeSeverity.OK),
        "warning": sum(1 for r in results if r.severity == RangeSeverity.WARNING),
        "critical": sum(1 for r in results if r.severity == RangeSeverity.CRITICAL),
        "total": len(results),
    }

    return results, summary


def calculate_range_validity_score(results: list[RangeCheckResult]) -> float:
    """Calculate a 0-100 score based on range validation results.

    Args:
        results: List of range check results

    Returns:
        Score from 0-100 (100 = all values in range)
    """
    if not results:
        return 100.0

    # Weights: OK=1, WARNING=0.5, CRITICAL=0
    weights = {
        RangeSeverity.OK: 1.0,
        RangeSeverity.WARNING: 0.5,
        RangeSeverity.CRITICAL: 0.0,
    }

    total_score = sum(weights[r.severity] for r in results)
    return (total_score / len(results)) * 100
