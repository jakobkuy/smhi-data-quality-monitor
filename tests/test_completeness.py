"""Tests for completeness validation."""

from datetime import datetime, timedelta

from src.validation.completeness import (
    analyze_completeness,
    calculate_completeness_score,
    format_gap_report,
)


class TestAnalyzeCompleteness:
    """Tests for analyze_completeness function."""

    def test_complete_dataset_returns_100(
        self, complete_timestamps: list[datetime]
    ) -> None:
        """Complete dataset returns 100% completeness."""
        result = analyze_completeness(
            complete_timestamps,
            expected_interval=timedelta(hours=1),
        )
        assert result.completeness_percent == 100.0
        assert result.passes_threshold is True
        assert len(result.gaps) == 0

    def test_dataset_with_gap_detected(
        self, timestamps_with_gap: list[datetime]
    ) -> None:
        """Gap in dataset is detected."""
        result = analyze_completeness(
            timestamps_with_gap,
            expected_interval=timedelta(hours=1),
        )
        assert len(result.gaps) == 1
        assert result.gaps[0].missing_count == 3  # Hours 3, 4, 5 missing
        assert result.longest_gap == result.gaps[0]

    def test_empty_dataset_returns_0(self) -> None:
        """Empty dataset returns 0% completeness."""
        result = analyze_completeness([])
        assert result.completeness_percent == 0.0
        assert result.passes_threshold is False

    def test_single_observation_valid(self) -> None:
        """Single observation is valid."""
        result = analyze_completeness([datetime.now()])
        assert result.total_present == 1
        assert result.completeness_percent == 100.0

    def test_custom_interval(self) -> None:
        """Custom interval is respected."""
        base = datetime(2024, 1, 1)
        # Every 15 minutes for 1 hour = 5 observations
        timestamps = [base + timedelta(minutes=15 * i) for i in range(5)]
        result = analyze_completeness(
            timestamps,
            expected_interval=timedelta(minutes=15),
        )
        assert result.total_expected == 5
        assert result.completeness_percent == 100.0

    def test_below_threshold_fails(self) -> None:
        """Dataset below threshold fails check."""
        base = datetime(2024, 1, 1)
        # Only 5 observations when 10 expected
        timestamps = [base + timedelta(hours=i * 2) for i in range(5)]
        result = analyze_completeness(
            timestamps,
            expected_interval=timedelta(hours=1),
            start_time=base,
            end_time=base + timedelta(hours=9),
            min_completeness=90.0,
        )
        assert result.passes_threshold is False

    def test_unsorted_timestamps_handled(self) -> None:
        """Unsorted timestamps are sorted before analysis."""
        base = datetime(2024, 1, 1)
        timestamps = [
            base + timedelta(hours=3),
            base + timedelta(hours=1),
            base + timedelta(hours=2),
            base,
        ]
        result = analyze_completeness(timestamps)
        assert result.total_present == 4


class TestCalculateCompletenessScore:
    """Tests for calculate_completeness_score function."""

    def test_score_equals_percent(self, complete_timestamps: list[datetime]) -> None:
        """Score equals completeness percentage."""
        result = analyze_completeness(complete_timestamps)
        score = calculate_completeness_score(result)
        assert score == result.completeness_percent


class TestFormatGapReport:
    """Tests for format_gap_report function."""

    def test_empty_gaps_returns_empty(self) -> None:
        """Empty gap list returns empty report."""
        report = format_gap_report([])
        assert report == []

    def test_gap_formatted_correctly(
        self, timestamps_with_gap: list[datetime]
    ) -> None:
        """Gaps are formatted with start, end, and duration."""
        result = analyze_completeness(
            timestamps_with_gap,
            expected_interval=timedelta(hours=1),
        )
        report = format_gap_report(result.gaps)
        assert len(report) == 1
        assert "Gap from" in report[0]
        assert "missing observations" in report[0]
