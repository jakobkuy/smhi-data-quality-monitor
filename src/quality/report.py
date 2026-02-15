"""Quality report generation."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.quality.scorer import QualityScore
from src.validation.anomaly_detector import Anomaly


@dataclass
class StationReport:
    """Quality report for a single station/parameter."""

    station_id: int
    station_name: str
    parameter_id: int
    parameter_name: str
    time_window_start: datetime
    time_window_end: datetime
    observation_count: int
    quality_score: QualityScore
    anomalies: list[Anomaly]
    generated_at: datetime


def generate_station_report(
    station_id: int,
    station_name: str,
    parameter_id: int,
    parameter_name: str,
    time_window_start: datetime,
    time_window_end: datetime,
    observation_count: int,
    quality_score: QualityScore,
    anomalies: list[Anomaly],
) -> StationReport:
    """Generate a quality report for a station/parameter.

    Args:
        station_id: Station identifier
        station_name: Human-readable station name
        parameter_id: Parameter identifier
        parameter_name: Parameter description
        time_window_start: Start of analysis period
        time_window_end: End of analysis period
        observation_count: Number of observations analyzed
        quality_score: Calculated quality score
        anomalies: List of detected anomalies

    Returns:
        StationReport with all quality metrics
    """
    return StationReport(
        station_id=station_id,
        station_name=station_name,
        parameter_id=parameter_id,
        parameter_name=parameter_name,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
        observation_count=observation_count,
        quality_score=quality_score,
        anomalies=anomalies,
        generated_at=datetime.now(),
    )


def reports_to_dataframe(reports: list[StationReport]) -> pd.DataFrame:
    """Convert list of reports to a pandas DataFrame.

    Args:
        reports: List of StationReport objects

    Returns:
        DataFrame with quality metrics for all stations
    """
    rows = []
    for r in reports:
        rows.append({
            "station_id": r.station_id,
            "station_name": r.station_name,
            "parameter_id": r.parameter_id,
            "parameter_name": r.parameter_name,
            "observation_count": r.observation_count,
            "overall_score": r.quality_score.overall,
            "grade": r.quality_score.grade,
            "schema_validity": r.quality_score.components.schema_validity,
            "completeness": r.quality_score.components.completeness,
            "range_validity": r.quality_score.components.range_validity,
            "anomaly_score": r.quality_score.components.anomaly_score,
            "anomaly_count": len(r.anomalies),
            "recommendation": r.quality_score.recommendation,
            "time_window_start": r.time_window_start,
            "time_window_end": r.time_window_end,
            "generated_at": r.generated_at,
        })

    return pd.DataFrame(rows)


def format_report_summary(report: StationReport) -> str:
    """Format a single report as human-readable text.

    Args:
        report: StationReport to format

    Returns:
        Formatted string summary
    """
    lines = [
        f"Quality Report: {report.station_name}",
        f"Parameter: {report.parameter_name}",
        f"Period: {report.time_window_start.date()} to {report.time_window_end.date()}",
        f"Observations: {report.observation_count}",
        "",
        f"Overall Score: {report.quality_score.overall}/100 (Grade: {report.quality_score.grade})",
        "",
        "Score Breakdown:",
        f"  Schema Validity: {report.quality_score.components.schema_validity:.0f}%",
        f"  Completeness: {report.quality_score.components.completeness:.0f}%",
        f"  Range Validity: {report.quality_score.components.range_validity:.0f}%",
        f"  Anomaly Score: {report.quality_score.components.anomaly_score:.0f}%",
        "",
        f"Anomalies Detected: {len(report.anomalies)}",
    ]

    if report.anomalies:
        lines.append("")
        lines.append("Top Anomalies:")
        for anomaly in report.anomalies[:5]:
            lines.append(
                f"  - {anomaly.timestamp}: {anomaly.value} ({anomaly.method.value})"
            )

    lines.append("")
    lines.append(f"Recommendation: {report.quality_score.recommendation}")

    return "\n".join(lines)


def generate_system_summary(reports: list[StationReport]) -> dict:
    """Generate a system-wide summary from all reports.

    Args:
        reports: List of all station reports

    Returns:
        Dictionary with system-wide metrics
    """
    if not reports:
        return {
            "total_stations": 0,
            "total_observations": 0,
            "average_score": 0.0,
            "grade_distribution": {},
            "total_anomalies": 0,
            "stations_with_issues": 0,
        }

    grade_dist: dict[str, int] = {}
    for r in reports:
        grade_dist[r.quality_score.grade] = grade_dist.get(r.quality_score.grade, 0) + 1

    return {
        "total_stations": len(reports),
        "total_observations": sum(r.observation_count for r in reports),
        "average_score": sum(r.quality_score.overall for r in reports) / len(reports),
        "grade_distribution": grade_dist,
        "total_anomalies": sum(len(r.anomalies) for r in reports),
        "stations_with_issues": sum(
            1 for r in reports if r.quality_score.grade in ("D", "F")
        ),
    }
