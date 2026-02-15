"""Data validation modules for quality assurance."""

from src.validation.anomaly_detector import (
    Anomaly,
    AnomalyMethod,
    AnomalySeverity,
    calculate_anomaly_rate,
    calculate_anomaly_score,
    detect_all_anomalies,
    detect_iqr_anomalies,
    detect_rate_of_change_anomalies,
    detect_zscore_anomalies,
)
from src.validation.completeness import (
    CompletenessResult,
    Gap,
    analyze_completeness,
    calculate_completeness_score,
    format_gap_report,
)
from src.validation.range_validator import (
    RangeCheckResult,
    RangeSeverity,
    calculate_range_validity_score,
    check_range,
    validate_observations,
)
from src.validation.schema_validator import (
    HydroObsResponse,
    MetObsResponse,
    ObservationValue,
    ValidationResult,
    ValidationSeverity,
    validate_observation_response,
    validate_station_list,
)

__all__ = [
    # Schema validation
    "ValidationResult",
    "ValidationSeverity",
    "MetObsResponse",
    "HydroObsResponse",
    "ObservationValue",
    "validate_observation_response",
    "validate_station_list",
    # Range validation
    "RangeCheckResult",
    "RangeSeverity",
    "check_range",
    "validate_observations",
    "calculate_range_validity_score",
    # Completeness
    "CompletenessResult",
    "Gap",
    "analyze_completeness",
    "calculate_completeness_score",
    "format_gap_report",
    # Anomaly detection
    "Anomaly",
    "AnomalyMethod",
    "AnomalySeverity",
    "detect_zscore_anomalies",
    "detect_iqr_anomalies",
    "detect_rate_of_change_anomalies",
    "detect_all_anomalies",
    "calculate_anomaly_rate",
    "calculate_anomaly_score",
]
