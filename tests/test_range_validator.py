"""Tests for range validation."""


from src.validation.range_validator import (
    RangeSeverity,
    calculate_range_validity_score,
    check_range,
    validate_observations,
)


class TestCheckRange:
    """Tests for check_range function."""

    def test_temperature_normal_value_ok(self) -> None:
        """Normal temperature returns OK."""
        result = check_range(20.0, "temperature")
        assert result.severity == RangeSeverity.OK
        assert result.value == 20.0

    def test_temperature_above_max_critical(self) -> None:
        """Temperature above 55°C is CRITICAL."""
        result = check_range(60.0, "temperature")
        assert result.severity == RangeSeverity.CRITICAL
        assert result.threshold_violated == "max"

    def test_temperature_below_min_critical(self) -> None:
        """Temperature below -60°C is CRITICAL."""
        result = check_range(-65.0, "temperature")
        assert result.severity == RangeSeverity.CRITICAL
        assert result.threshold_violated == "min"

    def test_temperature_above_warn_max_warning(self) -> None:
        """Temperature above 40°C but below 55°C is WARNING."""
        result = check_range(45.0, "temperature")
        assert result.severity == RangeSeverity.WARNING
        assert result.threshold_violated == "warn_max"

    def test_temperature_below_warn_min_warning(self) -> None:
        """Temperature below -50°C but above -60°C is WARNING."""
        result = check_range(-55.0, "temperature")
        assert result.severity == RangeSeverity.WARNING
        assert result.threshold_violated == "warn_min"

    def test_wind_speed_negative_critical(self) -> None:
        """Negative wind speed is CRITICAL (physically impossible)."""
        result = check_range(-5.0, "wind_speed")
        assert result.severity == RangeSeverity.CRITICAL

    def test_wind_speed_extreme_warning(self) -> None:
        """Very high wind speed is WARNING."""
        result = check_range(50.0, "wind_speed")
        assert result.severity == RangeSeverity.WARNING

    def test_humidity_at_boundary(self) -> None:
        """Humidity at 100% is OK (valid boundary)."""
        result = check_range(100.0, "humidity")
        assert result.severity == RangeSeverity.OK

    def test_humidity_over_100_critical(self) -> None:
        """Humidity over 100% is CRITICAL."""
        result = check_range(105.0, "humidity")
        assert result.severity == RangeSeverity.CRITICAL

    def test_unknown_parameter_ok(self) -> None:
        """Unknown parameter returns OK (no thresholds)."""
        result = check_range(999.0, "unknown_param")
        assert result.severity == RangeSeverity.OK

    def test_custom_thresholds_override(self) -> None:
        """Custom thresholds override defaults."""
        custom = {"min": 0, "max": 10, "warn_min": 2, "warn_max": 8}
        result = check_range(15.0, "temperature", custom_thresholds=custom)
        assert result.severity == RangeSeverity.CRITICAL


class TestValidateObservations:
    """Tests for validate_observations function."""

    def test_all_normal_values(self, temperature_values_normal: list[float]) -> None:
        """All normal values return all OK."""
        results, summary = validate_observations(
            temperature_values_normal, "temperature"
        )
        assert summary["ok"] == len(temperature_values_normal)
        assert summary["warning"] == 0
        assert summary["critical"] == 0

    def test_values_with_critical_outlier(
        self, temperature_values_with_critical_outlier: list[float]
    ) -> None:
        """Critical outlier is detected."""
        results, summary = validate_observations(
            temperature_values_with_critical_outlier, "temperature"
        )
        assert summary["critical"] == 1
        # Find the critical result
        critical = [r for r in results if r.severity == RangeSeverity.CRITICAL]
        assert len(critical) == 1
        assert critical[0].value == 100.0


class TestCalculateRangeValidityScore:
    """Tests for calculate_range_validity_score function."""

    def test_all_ok_returns_100(self) -> None:
        """All OK results returns score of 100."""
        results, _ = validate_observations([5.0, 10.0, 15.0], "temperature")
        score = calculate_range_validity_score(results)
        assert score == 100.0

    def test_all_critical_returns_0(self) -> None:
        """All critical results returns score of 0."""
        results, _ = validate_observations([100.0, -100.0], "temperature")
        score = calculate_range_validity_score(results)
        assert score == 0.0

    def test_mixed_results_proportional(self) -> None:
        """Mixed results return proportional score."""
        # 4 OK (1.0 each) + 1 WARNING (0.5) = 4.5 / 5 = 90%
        values = [5.0, 10.0, 15.0, 20.0, 45.0]  # 45.0 is warning
        results, _ = validate_observations(values, "temperature")
        score = calculate_range_validity_score(results)
        assert score == 90.0

    def test_empty_list_returns_100(self) -> None:
        """Empty list returns 100 (no failures)."""
        score = calculate_range_validity_score([])
        assert score == 100.0
