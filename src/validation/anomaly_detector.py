"""Statistical anomaly detection for sensor data."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import numpy as np

from src.utils.config import IQR_MULTIPLIER, RATE_OF_CHANGE_THRESHOLD, ZSCORE_THRESHOLD


class AnomalyMethod(str, Enum):
    """Detection method used to identify anomaly."""

    ZSCORE = "zscore"
    IQR = "iqr"
    RATE_OF_CHANGE = "rate_of_change"


class AnomalySeverity(str, Enum):
    """Severity of detected anomaly."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Anomaly:
    """A detected anomaly in the data."""

    timestamp: datetime
    value: float
    method: AnomalyMethod
    severity: AnomalySeverity
    message: str
    deviation: float  # How far from expected (z-score or IQR multiple)


def detect_zscore_anomalies(
    values: list[float],
    timestamps: list[datetime],
    threshold: float = ZSCORE_THRESHOLD,
    window_size: int | None = None,
) -> list[Anomaly]:
    """Detect anomalies using z-score method.

    Args:
        values: List of measured values
        timestamps: Corresponding timestamps
        threshold: Z-score threshold for anomaly detection
        window_size: Rolling window size (None = use all data)

    Returns:
        List of detected anomalies
    """
    if len(values) < 3:
        return []

    arr = np.array(values)
    anomalies: list[Anomaly] = []

    if window_size and window_size < len(arr):
        # Rolling z-score
        for i in range(window_size, len(arr)):
            window = arr[i - window_size : i]
            mean = np.mean(window)
            std = np.std(window)
            if std > 0:
                z = abs((arr[i] - mean) / std)
                if z > threshold:
                    severity = _zscore_to_severity(z)
                    anomalies.append(
                        Anomaly(
                            timestamp=timestamps[i],
                            value=values[i],
                            method=AnomalyMethod.ZSCORE,
                            severity=severity,
                            message=f"Value {values[i]} is {z:.1f} std devs from rolling mean",
                            deviation=z,
                        )
                    )
    else:
        # Global z-score
        mean = np.mean(arr)
        std = np.std(arr)
        if std > 0:
            z_scores = np.abs((arr - mean) / std)
            for i, z in enumerate(z_scores):
                if z > threshold:
                    severity = _zscore_to_severity(z)
                    anomalies.append(
                        Anomaly(
                            timestamp=timestamps[i],
                            value=values[i],
                            method=AnomalyMethod.ZSCORE,
                            severity=severity,
                            message=f"Value {values[i]} is {z:.1f} std devs from mean",
                            deviation=z,
                        )
                    )

    return anomalies


def detect_iqr_anomalies(
    values: list[float],
    timestamps: list[datetime],
    multiplier: float = IQR_MULTIPLIER,
) -> list[Anomaly]:
    """Detect anomalies using IQR (Interquartile Range) method.

    Args:
        values: List of measured values
        timestamps: Corresponding timestamps
        multiplier: IQR multiplier for outlier bounds

    Returns:
        List of detected anomalies
    """
    if len(values) < 4:
        return []

    arr = np.array(values)
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1

    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)

    anomalies: list[Anomaly] = []
    for i, val in enumerate(values):
        if val < lower_bound:
            deviation = (q1 - val) / iqr if iqr > 0 else 0
            anomalies.append(
                Anomaly(
                    timestamp=timestamps[i],
                    value=val,
                    method=AnomalyMethod.IQR,
                    severity=_iqr_deviation_to_severity(deviation),
                    message=f"Value {val} is below IQR lower bound {lower_bound:.2f}",
                    deviation=deviation,
                )
            )
        elif val > upper_bound:
            deviation = (val - q3) / iqr if iqr > 0 else 0
            anomalies.append(
                Anomaly(
                    timestamp=timestamps[i],
                    value=val,
                    method=AnomalyMethod.IQR,
                    severity=_iqr_deviation_to_severity(deviation),
                    message=f"Value {val} is above IQR upper bound {upper_bound:.2f}",
                    deviation=deviation,
                )
            )

    return anomalies


def detect_rate_of_change_anomalies(
    values: list[float],
    timestamps: list[datetime],
    parameter: str,
    custom_threshold: float | None = None,
) -> list[Anomaly]:
    """Detect anomalies based on rapid rate of change.

    Args:
        values: List of measured values
        timestamps: Corresponding timestamps
        parameter: Parameter type for threshold lookup
        custom_threshold: Override threshold value

    Returns:
        List of detected anomalies
    """
    if len(values) < 2:
        return []

    threshold = custom_threshold or RATE_OF_CHANGE_THRESHOLD.get(parameter, float("inf"))
    anomalies: list[Anomaly] = []

    for i in range(1, len(values)):
        change = abs(values[i] - values[i - 1])
        if change > threshold:
            severity = _rate_change_to_severity(change, threshold)
            anomalies.append(
                Anomaly(
                    timestamp=timestamps[i],
                    value=values[i],
                    method=AnomalyMethod.RATE_OF_CHANGE,
                    severity=severity,
                    message=f"Rapid change of {change:.2f} from previous value {values[i-1]}",
                    deviation=change / threshold,
                )
            )

    return anomalies


def detect_all_anomalies(
    values: list[float],
    timestamps: list[datetime],
    parameter: str,
    methods: list[AnomalyMethod] | None = None,
) -> list[Anomaly]:
    """Run all specified anomaly detection methods.

    Args:
        values: List of measured values
        timestamps: Corresponding timestamps
        parameter: Parameter type
        methods: List of methods to use (default: all)

    Returns:
        Combined list of all detected anomalies (deduplicated by timestamp)
    """
    if methods is None:
        methods = list(AnomalyMethod)

    all_anomalies: list[Anomaly] = []

    if AnomalyMethod.ZSCORE in methods:
        all_anomalies.extend(detect_zscore_anomalies(values, timestamps))

    if AnomalyMethod.IQR in methods:
        all_anomalies.extend(detect_iqr_anomalies(values, timestamps))

    if AnomalyMethod.RATE_OF_CHANGE in methods:
        all_anomalies.extend(
            detect_rate_of_change_anomalies(values, timestamps, parameter)
        )

    # Sort by timestamp
    all_anomalies.sort(key=lambda a: a.timestamp)

    return all_anomalies


def calculate_anomaly_rate(
    anomalies: list[Anomaly],
    total_observations: int,
) -> float:
    """Calculate the percentage of observations that are anomalous.

    Args:
        anomalies: List of detected anomalies
        total_observations: Total number of observations

    Returns:
        Anomaly rate as percentage (0-100)
    """
    if total_observations == 0:
        return 0.0
    return (len(anomalies) / total_observations) * 100


def calculate_anomaly_score(anomaly_rate: float) -> float:
    """Convert anomaly rate to quality score (inverse relationship).

    Args:
        anomaly_rate: Percentage of anomalous observations

    Returns:
        Quality score from 0-100 (100 = no anomalies)
    """
    return max(0.0, 100.0 - anomaly_rate)


def _zscore_to_severity(z: float) -> AnomalySeverity:
    """Map z-score to severity level."""
    if z > 5:
        return AnomalySeverity.HIGH
    elif z > 4:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW


def _iqr_deviation_to_severity(deviation: float) -> AnomalySeverity:
    """Map IQR deviation to severity level."""
    if deviation > 3:
        return AnomalySeverity.HIGH
    elif deviation > 2:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW


def _rate_change_to_severity(change: float, threshold: float) -> AnomalySeverity:
    """Map rate of change to severity level."""
    ratio = change / threshold
    if ratio > 3:
        return AnomalySeverity.HIGH
    elif ratio > 2:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW
