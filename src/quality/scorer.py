"""Composite data quality scoring system."""

from dataclasses import dataclass

from src.utils.config import QUALITY_WEIGHTS


@dataclass
class QualityComponents:
    """Individual components of the quality score."""

    schema_validity: float  # 0-100
    completeness: float     # 0-100
    range_validity: float   # 0-100
    anomaly_score: float    # 0-100 (100 = no anomalies)


@dataclass
class QualityScore:
    """Complete quality score with breakdown."""

    overall: float  # 0-100 weighted composite
    components: QualityComponents
    grade: str  # A, B, C, D, F
    recommendation: str


def calculate_quality_score(
    schema_valid: bool,
    completeness_percent: float,
    range_validity_percent: float,
    anomaly_rate_percent: float,
    weights: dict[str, float] | None = None,
) -> QualityScore:
    """Calculate composite data quality score.

    Args:
        schema_valid: Whether schema validation passed
        completeness_percent: Data completeness (0-100)
        range_validity_percent: Percentage of values in valid range (0-100)
        anomaly_rate_percent: Percentage of anomalous values (0-100)
        weights: Optional custom weights (must sum to 1.0)

    Returns:
        QualityScore with overall score and breakdown
    """
    weights = weights or QUALITY_WEIGHTS

    # Convert inputs to component scores
    components = QualityComponents(
        schema_validity=100.0 if schema_valid else 0.0,
        completeness=min(100.0, max(0.0, completeness_percent)),
        range_validity=min(100.0, max(0.0, range_validity_percent)),
        anomaly_score=min(100.0, max(0.0, 100.0 - anomaly_rate_percent)),
    )

    # Calculate weighted overall score
    overall = (
        components.schema_validity * weights["schema_validity"]
        + components.completeness * weights["completeness"]
        + components.range_validity * weights["range_validity"]
        + components.anomaly_score * weights["anomaly_rate"]
    )

    # Determine grade
    grade = _score_to_grade(overall)

    # Generate recommendation
    recommendation = _generate_recommendation(components, overall)

    return QualityScore(
        overall=round(overall, 1),
        components=components,
        grade=grade,
        recommendation=recommendation,
    )


def aggregate_station_scores(scores: list[QualityScore]) -> QualityScore:
    """Aggregate multiple station scores into an overall system score.

    Args:
        scores: List of individual station quality scores

    Returns:
        Aggregated quality score
    """
    if not scores:
        return QualityScore(
            overall=0.0,
            components=QualityComponents(
                schema_validity=0.0,
                completeness=0.0,
                range_validity=0.0,
                anomaly_score=0.0,
            ),
            grade="F",
            recommendation="No data available for quality assessment",
        )

    # Average each component
    avg_schema = sum(s.components.schema_validity for s in scores) / len(scores)
    avg_completeness = sum(s.components.completeness for s in scores) / len(scores)
    avg_range = sum(s.components.range_validity for s in scores) / len(scores)
    avg_anomaly = sum(s.components.anomaly_score for s in scores) / len(scores)

    components = QualityComponents(
        schema_validity=avg_schema,
        completeness=avg_completeness,
        range_validity=avg_range,
        anomaly_score=avg_anomaly,
    )

    overall = sum(s.overall for s in scores) / len(scores)
    grade = _score_to_grade(overall)

    # Count stations by grade
    grade_counts = {}
    for s in scores:
        grade_counts[s.grade] = grade_counts.get(s.grade, 0) + 1

    recommendation = _generate_system_recommendation(grade_counts, overall)

    return QualityScore(
        overall=round(overall, 1),
        components=components,
        grade=grade,
        recommendation=recommendation,
    )


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def _generate_recommendation(components: QualityComponents, overall: float) -> str:
    """Generate actionable recommendation based on score components."""
    issues = []

    if components.schema_validity < 100:
        issues.append("API response schema validation failed - check API compatibility")

    if components.completeness < 90:
        issues.append(
            f"Data completeness is low ({components.completeness:.0f}%) - investigate gaps"
        )

    if components.range_validity < 90:
        issues.append(
            f"Range validity concerns ({components.range_validity:.0f}%) - sensor calibration may be needed"
        )

    if components.anomaly_score < 90:
        anomaly_rate = 100 - components.anomaly_score
        issues.append(
            f"Elevated anomaly rate ({anomaly_rate:.1f}%) - review flagged values"
        )

    if not issues:
        return "Data quality is excellent - no action required"

    return "; ".join(issues)


def _generate_system_recommendation(
    grade_counts: dict[str, int],
    overall: float,
) -> str:
    """Generate system-wide recommendation."""
    total = sum(grade_counts.values())
    poor_stations = grade_counts.get("D", 0) + grade_counts.get("F", 0)

    if overall >= 90:
        return f"System health excellent across {total} stations"
    elif poor_stations > 0:
        return (
            f"{poor_stations} of {total} stations have degraded data quality - "
            "investigate sensor issues"
        )
    elif overall >= 70:
        return f"System health acceptable - minor issues at some stations"
    else:
        return "System-wide data quality concerns - comprehensive review needed"
