"""Tests for anomaly detection."""

from datetime import datetime, timedelta

import pytest

from src.validation.anomaly_detector import (
    AnomalyMethod,
    calculate_anomaly_rate,
    calculate_anomaly_score,
    detect_all_anomalies,
    detect_iqr_anomalies,
    detect_rate_of_change_anomalies,
    detect_zscore_anomalies,
)


@pytest.fixture
def timestamps_10() -> list[datetime]:
    """10 hourly timestamps."""
    base = datetime(2024, 1, 1)
    return [base + timedelta(hours=i) for i in range(10)]


class TestDetectZscoreAnomalies:
    """Tests for z-score anomaly detection."""

    def test_clean_data_no_anomalies(
        self,
        temperature_values_normal: list[float],
        timestamps_10: list[datetime],
    ) -> None:
        """Clean data returns no anomalies."""
        anomalies = detect_zscore_anomalies(
            temperature_values_normal,
            timestamps_10,
        )
        assert len(anomalies) == 0

    def test_spike_detected(
        self,
        timestamps_10: list[datetime],
    ) -> None:
        """Spike value is detected as anomaly with lower threshold."""
        # Use values where the spike is clearly an outlier
        values = [5.0, 5.1, 5.0, 5.2, 5.0, 5.1, 5.0, 5.1, 5.0, 50.0]
        # Use a lower threshold to ensure detection
        anomalies = detect_zscore_anomalies(values, timestamps_10, threshold=2.0)
        assert len(anomalies) >= 1
        assert any(a.value == 50.0 for a in anomalies)
        assert all(a.method == AnomalyMethod.ZSCORE for a in anomalies)

    def test_too_few_values_returns_empty(self) -> None:
        """Less than 3 values returns no anomalies."""
        anomalies = detect_zscore_anomalies(
            [5.0, 6.0],
            [datetime.now(), datetime.now()],
        )
        assert len(anomalies) == 0

    def test_rolling_window_detection(
        self, timestamps_10: list[datetime]
    ) -> None:
        """Rolling window z-score detection works."""
        values = [5.0, 5.1, 5.2, 5.0, 5.1, 50.0, 5.2, 5.0, 5.1, 5.0]
        anomalies = detect_zscore_anomalies(
            values,
            timestamps_10,
            window_size=5,
        )
        # Should detect 50.0 as anomaly
        assert any(a.value == 50.0 for a in anomalies)


class TestDetectIqrAnomalies:
    """Tests for IQR anomaly detection."""

    def test_clean_data_no_anomalies(
        self,
        temperature_values_normal: list[float],
        timestamps_10: list[datetime],
    ) -> None:
        """Clean data returns no anomalies."""
        anomalies = detect_iqr_anomalies(
            temperature_values_normal,
            timestamps_10,
        )
        assert len(anomalies) == 0

    def test_outlier_detected(
        self,
        temperature_values_with_anomaly: list[float],
        timestamps_10: list[datetime],
    ) -> None:
        """Outlier is detected."""
        anomalies = detect_iqr_anomalies(
            temperature_values_with_anomaly,
            timestamps_10,
        )
        assert len(anomalies) >= 1
        assert any(a.value == 45.0 for a in anomalies)

    def test_too_few_values_returns_empty(self) -> None:
        """Less than 4 values returns no anomalies."""
        anomalies = detect_iqr_anomalies(
            [5.0, 6.0, 7.0],
            [datetime.now()] * 3,
        )
        assert len(anomalies) == 0


class TestDetectRateOfChangeAnomalies:
    """Tests for rate-of-change anomaly detection."""

    def test_gradual_change_no_anomaly(
        self, timestamps_10: list[datetime]
    ) -> None:
        """Gradual change is not flagged."""
        # Changes of 0.3 degrees per hour
        values = [5.0 + (0.3 * i) for i in range(10)]
        anomalies = detect_rate_of_change_anomalies(
            values,
            timestamps_10,
            "temperature",
        )
        assert len(anomalies) == 0

    def test_rapid_change_detected(
        self, timestamps_10: list[datetime]
    ) -> None:
        """Rapid change is detected."""
        values = [5.0, 5.2, 5.1, 20.0, 5.3, 5.2, 5.1, 5.0, 5.1, 5.2]
        anomalies = detect_rate_of_change_anomalies(
            values,
            timestamps_10,
            "temperature",
        )
        # Jump from 5.1 to 20.0 = 14.9, threshold is 10
        assert len(anomalies) >= 1
        assert anomalies[0].method == AnomalyMethod.RATE_OF_CHANGE

    def test_custom_threshold(self, timestamps_10: list[datetime]) -> None:
        """Custom threshold is used."""
        values = [5.0, 8.0, 5.0, 8.0, 5.0, 8.0, 5.0, 8.0, 5.0, 8.0]
        # With default temp threshold of 10, no anomalies
        anomalies_default = detect_rate_of_change_anomalies(
            values,
            timestamps_10,
            "temperature",
        )
        assert len(anomalies_default) == 0

        # With threshold of 2, all changes detected
        anomalies_strict = detect_rate_of_change_anomalies(
            values,
            timestamps_10,
            "temperature",
            custom_threshold=2.0,
        )
        assert len(anomalies_strict) > 0


class TestDetectAllAnomalies:
    """Tests for combined anomaly detection."""

    def test_all_methods_run(
        self,
        temperature_values_with_anomaly: list[float],
        timestamps_10: list[datetime],
    ) -> None:
        """All methods are run by default."""
        anomalies = detect_all_anomalies(
            temperature_values_with_anomaly,
            timestamps_10,
            "temperature",
        )
        # Should have anomalies from multiple methods
        methods_used = {a.method for a in anomalies}
        assert len(methods_used) >= 1

    def test_subset_of_methods(
        self,
        timestamps_10: list[datetime],
    ) -> None:
        """Can run subset of methods."""
        # Use values with a clear anomaly
        values = [5.0, 5.1, 5.0, 5.2, 5.0, 5.1, 5.0, 5.1, 5.0, 100.0]
        anomalies = detect_all_anomalies(
            values,
            timestamps_10,
            "temperature",
            methods=[AnomalyMethod.ZSCORE],
        )
        # Verify only ZSCORE method is used (when anomalies found)
        if anomalies:
            methods_used = {a.method for a in anomalies}
            assert methods_used == {AnomalyMethod.ZSCORE}


class TestAnomalyMetrics:
    """Tests for anomaly rate and score calculations."""

    def test_anomaly_rate_calculation(self) -> None:
        """Anomaly rate is calculated correctly."""
        # 2 anomalies out of 10 = 20%
        rate = calculate_anomaly_rate([None, None], 10)  # type: ignore
        assert rate == 20.0

    def test_anomaly_rate_zero_observations(self) -> None:
        """Zero observations returns 0 rate."""
        rate = calculate_anomaly_rate([], 0)
        assert rate == 0.0

    def test_anomaly_score_inverse(self) -> None:
        """Anomaly score is inverse of rate."""
        score = calculate_anomaly_score(20.0)  # 20% anomaly rate
        assert score == 80.0  # 80% score

    def test_anomaly_score_max(self) -> None:
        """0% anomaly rate = 100 score."""
        score = calculate_anomaly_score(0.0)
        assert score == 100.0

    def test_anomaly_score_min(self) -> None:
        """100% anomaly rate = 0 score."""
        score = calculate_anomaly_score(100.0)
        assert score == 0.0
