"""Tests for quality scoring."""

import pytest

from src.quality.scorer import (
    QualityScore,
    aggregate_station_scores,
    calculate_quality_score,
)


class TestCalculateQualityScore:
    """Tests for calculate_quality_score function."""

    def test_perfect_data_returns_100(self) -> None:
        """Perfect data returns score of 100."""
        score = calculate_quality_score(
            schema_valid=True,
            completeness_percent=100.0,
            range_validity_percent=100.0,
            anomaly_rate_percent=0.0,
        )
        assert score.overall == 100.0
        assert score.grade == "A"

    def test_all_failures_returns_0(self) -> None:
        """All failures return score of 0."""
        score = calculate_quality_score(
            schema_valid=False,
            completeness_percent=0.0,
            range_validity_percent=0.0,
            anomaly_rate_percent=100.0,
        )
        assert score.overall == 0.0
        assert score.grade == "F"

    def test_schema_failure_reduces_score(self) -> None:
        """Schema failure reduces score by 20%."""
        score_valid = calculate_quality_score(
            schema_valid=True,
            completeness_percent=100.0,
            range_validity_percent=100.0,
            anomaly_rate_percent=0.0,
        )
        score_invalid = calculate_quality_score(
            schema_valid=False,
            completeness_percent=100.0,
            range_validity_percent=100.0,
            anomaly_rate_percent=0.0,
        )
        assert score_valid.overall - score_invalid.overall == 20.0

    def test_weights_applied_correctly(self) -> None:
        """Default weights are applied correctly."""
        # 50% completeness with 30% weight = 15 points
        # All else perfect = 20 + 25 + 25 = 70 points
        # Total = 85
        score = calculate_quality_score(
            schema_valid=True,
            completeness_percent=50.0,
            range_validity_percent=100.0,
            anomaly_rate_percent=0.0,
        )
        assert score.overall == 85.0
        assert score.grade == "B"

    def test_grade_boundaries(self) -> None:
        """Test grade boundary values."""
        # A: >= 90 (100% everything = 100)
        assert calculate_quality_score(True, 100, 100, 0).grade == "A"

        # B: 80-89 (need to reduce score to 80-89 range)
        # schema=20, completeness=50*0.3=15, range=100*0.25=25, anomaly=100*0.25=25 = 85
        assert calculate_quality_score(True, 50, 100, 0).grade == "B"

        # C: 70-79
        # schema=20, completeness=30*0.3=9, range=100*0.25=25, anomaly=100*0.25=25 = 79
        assert calculate_quality_score(True, 30, 100, 0).grade == "C"

        # D: 60-69
        # schema=0, completeness=100*0.3=30, range=100*0.25=25, anomaly=50*0.25=12.5 = 67.5
        assert calculate_quality_score(False, 100, 100, 50).grade == "D"

        # F: < 60
        assert calculate_quality_score(False, 30, 50, 50).grade == "F"

    def test_recommendation_generated_for_issues(self) -> None:
        """Recommendations are generated for quality issues."""
        score = calculate_quality_score(
            schema_valid=True,
            completeness_percent=80.0,  # Below 90%
            range_validity_percent=100.0,
            anomaly_rate_percent=0.0,
        )
        assert "completeness" in score.recommendation.lower()

    def test_recommendation_excellent_when_perfect(self) -> None:
        """Perfect score gets 'excellent' recommendation."""
        score = calculate_quality_score(True, 100, 100, 0)
        assert "excellent" in score.recommendation.lower()

    def test_custom_weights(self) -> None:
        """Custom weights are applied."""
        custom_weights = {
            "schema_validity": 0.50,
            "completeness": 0.50,
            "range_validity": 0.0,
            "anomaly_rate": 0.0,
        }
        score = calculate_quality_score(
            schema_valid=True,
            completeness_percent=100.0,
            range_validity_percent=0.0,  # Would hurt with default weights
            anomaly_rate_percent=100.0,  # Would hurt with default weights
            weights=custom_weights,
        )
        assert score.overall == 100.0


class TestAggregateStationScores:
    """Tests for aggregate_station_scores function."""

    def test_empty_list_returns_zero(self) -> None:
        """Empty list returns zero score."""
        score = aggregate_station_scores([])
        assert score.overall == 0.0
        assert score.grade == "F"

    def test_single_station(self) -> None:
        """Single station returns its score."""
        station_score = calculate_quality_score(True, 90, 90, 5)
        aggregated = aggregate_station_scores([station_score])
        assert aggregated.overall == station_score.overall

    def test_multiple_stations_averaged(self) -> None:
        """Multiple station scores are averaged."""
        score1 = calculate_quality_score(True, 100, 100, 0)  # 100
        score2 = calculate_quality_score(True, 80, 80, 20)   # Lower
        aggregated = aggregate_station_scores([score1, score2])

        expected_avg = (score1.overall + score2.overall) / 2
        assert aggregated.overall == pytest.approx(expected_avg, 0.1)

    def test_recommendation_mentions_issues(self) -> None:
        """System recommendation mentions stations with issues."""
        good_score = calculate_quality_score(True, 100, 100, 0)
        bad_score = calculate_quality_score(False, 50, 50, 50)  # Grade F

        aggregated = aggregate_station_scores([good_score, bad_score])
        assert "1" in aggregated.recommendation  # 1 station with issues
