"""Data completeness validation for time series."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils.config import MIN_COMPLETENESS_PERCENT


@dataclass
class Gap:
    """Represents a gap in time series data."""

    start: datetime
    end: datetime
    duration: timedelta
    missing_count: int


@dataclass
class CompletenessResult:
    """Result of completeness analysis."""

    total_expected: int
    total_present: int
    completeness_percent: float
    gaps: list[Gap]
    longest_gap: Gap | None
    passes_threshold: bool


def analyze_completeness(
    timestamps: list[datetime],
    expected_interval: timedelta = timedelta(hours=1),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    min_completeness: float = MIN_COMPLETENESS_PERCENT,
) -> CompletenessResult:
    """Analyze completeness of a time series.

    Args:
        timestamps: List of observation timestamps (should be sorted)
        expected_interval: Expected time between observations
        start_time: Start of analysis window (default: first timestamp)
        end_time: End of analysis window (default: last timestamp)
        min_completeness: Minimum acceptable completeness percentage

    Returns:
        CompletenessResult with gap analysis
    """
    if not timestamps:
        return CompletenessResult(
            total_expected=0,
            total_present=0,
            completeness_percent=0.0,
            gaps=[],
            longest_gap=None,
            passes_threshold=False,
        )

    # Sort timestamps
    sorted_ts = sorted(timestamps)
    start = start_time or sorted_ts[0]
    end = end_time or sorted_ts[-1]

    # Calculate expected observations
    time_span = end - start
    total_expected = max(1, int(time_span / expected_interval) + 1)
    total_present = len(sorted_ts)

    # Find gaps
    gaps: list[Gap] = []
    gap_threshold = expected_interval * 1.5  # Allow some tolerance

    for i in range(len(sorted_ts) - 1):
        delta = sorted_ts[i + 1] - sorted_ts[i]
        if delta > gap_threshold:
            missing = int(delta / expected_interval) - 1
            gaps.append(
                Gap(
                    start=sorted_ts[i],
                    end=sorted_ts[i + 1],
                    duration=delta,
                    missing_count=missing,
                )
            )

    # Find longest gap
    longest_gap = max(gaps, key=lambda g: g.duration) if gaps else None

    # Calculate completeness percentage
    completeness = (total_present / total_expected) * 100 if total_expected > 0 else 0
    completeness = min(100.0, completeness)  # Cap at 100%

    return CompletenessResult(
        total_expected=total_expected,
        total_present=total_present,
        completeness_percent=completeness,
        gaps=gaps,
        longest_gap=longest_gap,
        passes_threshold=completeness >= min_completeness,
    )


def calculate_completeness_score(result: CompletenessResult) -> float:
    """Convert completeness result to a 0-100 quality score.

    Args:
        result: CompletenessResult from analyze_completeness

    Returns:
        Score from 0-100
    """
    return result.completeness_percent


def format_gap_report(gaps: list[Gap]) -> list[str]:
    """Format gaps as human-readable strings.

    Args:
        gaps: List of Gap objects

    Returns:
        List of formatted gap descriptions
    """
    return [
        f"Gap from {g.start.isoformat()} to {g.end.isoformat()} "
        f"({g.duration}, {g.missing_count} missing observations)"
        for g in gaps
    ]
