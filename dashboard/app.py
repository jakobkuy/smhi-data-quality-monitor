"""Streamlit dashboard for SMHI Data Quality Monitor."""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.api.metobs_client import MetObsClient, ObservationSet
from src.quality.report import generate_station_report, generate_system_summary
from src.quality.scorer import calculate_quality_score
from src.utils.config import (
    DEFAULT_STATIONS_METOBS,
    PARAM_HUMIDITY,
    PARAM_PRECIPITATION,
    PARAM_TEMPERATURE,
    PARAM_WIND_SPEED,
)
from src.utils.logging_config import configure_logging
from src.validation.anomaly_detector import detect_all_anomalies
from src.validation.completeness import analyze_completeness
from src.validation.range_validator import validate_observations
from src.validation.schema_validator import validate_observation_response

# Page configuration
st.set_page_config(
    page_title="SMHI Data Quality Monitor",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize logging
configure_logging(level="WARNING")

# Parameter mapping
PARAMETERS = {
    "Temperature (°C)": PARAM_TEMPERATURE,
    "Wind Speed (m/s)": PARAM_WIND_SPEED,
    "Humidity (%)": PARAM_HUMIDITY,
    "Precipitation (mm)": PARAM_PRECIPITATION,
}

PARAM_NAMES = {
    PARAM_TEMPERATURE: "temperature",
    PARAM_WIND_SPEED: "wind_speed",
    PARAM_HUMIDITY: "humidity",
    PARAM_PRECIPITATION: "precipitation",
}


@st.cache_data(ttl=300)
def fetch_observations(station_id: int, parameter_id: int) -> ObservationSet | None:
    """Fetch observations with caching."""
    try:
        client = MetObsClient()
        return client.get_observations(
            parameter_id=parameter_id,
            station_id=station_id,
            period="latest-months",
        )
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return None


def analyze_quality(observations: ObservationSet, parameter_name: str) -> dict:
    """Run full quality analysis on observation data."""
    values = [obs.value for obs in observations.observations]
    timestamps = [obs.timestamp for obs in observations.observations]

    # Schema validation (we already have parsed data, so it passed)
    schema_valid = True

    # Range validation
    range_results, range_summary = validate_observations(values, parameter_name)
    range_validity = (range_summary["ok"] / range_summary["total"] * 100) if range_summary["total"] > 0 else 100

    # Completeness
    completeness_result = analyze_completeness(timestamps)

    # Anomaly detection
    anomalies = detect_all_anomalies(values, timestamps, parameter_name)
    anomaly_rate = (len(anomalies) / len(values) * 100) if values else 0

    # Quality score
    quality_score = calculate_quality_score(
        schema_valid=schema_valid,
        completeness_percent=completeness_result.completeness_percent,
        range_validity_percent=range_validity,
        anomaly_rate_percent=anomaly_rate,
    )

    return {
        "quality_score": quality_score,
        "completeness": completeness_result,
        "range_summary": range_summary,
        "anomalies": anomalies,
        "values": values,
        "timestamps": timestamps,
    }


def render_sidebar():
    """Render sidebar controls."""
    st.sidebar.title("🌡️ SMHI Monitor")
    st.sidebar.markdown("---")

    # Station selection
    station_options = {s.name: s.id for s in DEFAULT_STATIONS_METOBS}
    selected_station_name = st.sidebar.selectbox(
        "Select Station",
        options=list(station_options.keys()),
    )
    selected_station_id = station_options[selected_station_name]

    # Parameter selection
    selected_param_name = st.sidebar.selectbox(
        "Select Parameter",
        options=list(PARAMETERS.keys()),
    )
    selected_param_id = PARAMETERS[selected_param_name]

    st.sidebar.markdown("---")

    # Multi-station selection for comparison
    st.sidebar.markdown("### Comparison View")
    comparison_stations = st.sidebar.multiselect(
        "Compare Stations",
        options=list(station_options.keys()),
        default=list(station_options.keys())[:3],
        help="Select 2+ stations to compare in the Comparison tab",
    )
    comparison_station_ids = [station_options[name] for name in comparison_stations]

    st.sidebar.markdown("---")

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **Data Source:** SMHI Open Data API
        **License:** CC BY 4.0
        """
    )

    return (
        selected_station_id,
        selected_station_name,
        selected_param_id,
        selected_param_name,
        comparison_stations,
        comparison_station_ids,
    )


def render_overview_tab(analysis: dict, station_name: str, param_name: str):
    """Render the overview tab."""
    score = analysis["quality_score"]

    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        color = "green" if score.overall >= 80 else "orange" if score.overall >= 60 else "red"
        st.metric(
            "Quality Score",
            f"{score.overall:.0f}/100",
            delta=f"Grade: {score.grade}",
        )

    with col2:
        st.metric(
            "Completeness",
            f"{analysis['completeness'].completeness_percent:.1f}%",
        )

    with col3:
        st.metric(
            "Observations",
            len(analysis["values"]),
        )

    with col4:
        st.metric(
            "Anomalies",
            len(analysis["anomalies"]),
        )

    st.markdown("---")

    # Score breakdown
    st.subheader("Score Breakdown")
    components = score.components

    breakdown_df = pd.DataFrame({
        "Component": ["Schema Validity", "Completeness", "Range Validity", "Anomaly Score"],
        "Score": [
            components.schema_validity,
            components.completeness,
            components.range_validity,
            components.anomaly_score,
        ],
        "Weight": ["20%", "30%", "25%", "25%"],
    })

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            breakdown_df,
            x="Component",
            y="Score",
            color="Score",
            color_continuous_scale=["red", "orange", "green"],
            range_color=[0, 100],
        )
        fig.update_layout(
            showlegend=False,
            yaxis_range=[0, 100],
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Recommendation")
        st.info(score.recommendation)

    # Gauge chart
    st.subheader("Overall Quality")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score.overall,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, 60], "color": "lightcoral"},
                {"range": [60, 80], "color": "lightyellow"},
                {"range": [80, 100], "color": "lightgreen"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 80,
            },
        },
        title={"text": f"{station_name} - {param_name}"},
    ))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)


def render_timeseries_tab(analysis: dict, param_name: str):
    """Render the time series explorer tab."""
    df = pd.DataFrame({
        "timestamp": analysis["timestamps"],
        "value": analysis["values"],
    })

    # Mark anomalies
    anomaly_times = {a.timestamp for a in analysis["anomalies"]}
    df["is_anomaly"] = df["timestamp"].isin(anomaly_times)

    # Main time series plot
    fig = go.Figure()

    # Normal points
    normal_df = df[~df["is_anomaly"]]
    fig.add_trace(go.Scatter(
        x=normal_df["timestamp"],
        y=normal_df["value"],
        mode="lines+markers",
        name="Normal",
        line={"color": "blue"},
        marker={"size": 4},
    ))

    # Anomaly points
    anomaly_df = df[df["is_anomaly"]]
    if len(anomaly_df) > 0:
        fig.add_trace(go.Scatter(
            x=anomaly_df["timestamp"],
            y=anomaly_df["value"],
            mode="markers",
            name="Anomaly",
            marker={"color": "red", "size": 10, "symbol": "x"},
        ))

    fig.update_layout(
        title="Time Series with Anomaly Detection",
        xaxis_title="Time",
        yaxis_title=param_name,
        hovermode="x unified",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mean", f"{df['value'].mean():.2f}")
    with col2:
        st.metric("Std Dev", f"{df['value'].std():.2f}")
    with col3:
        st.metric("Min", f"{df['value'].min():.2f}")
    with col4:
        st.metric("Max", f"{df['value'].max():.2f}")


def classify_anomaly_scope(
    station_anomalies: dict[str, set],
    threshold_percent: float = 50.0,
    time_window: timedelta = timedelta(hours=1),
) -> list[dict]:
    """
    Classify anomalies as sensor issues vs real phenomena.

    Args:
        station_anomalies: Dict mapping station names to their anomaly timestamps
        threshold_percent: If anomaly appears in >= this % of stations, it's "real"
        time_window: Timestamps within this window are considered "simultaneous"

    Returns:
        List of dicts with keys: timestamp, classification, affected_stations
        classification should be "sensor_issue" or "weather_event"
    """
    if not station_anomalies:
        return []

    total_stations = len(station_anomalies)
    if total_stations == 0:
        return []

    # Collect all unique anomaly timestamps
    all_timestamps: set[datetime] = set()
    for timestamps in station_anomalies.values():
        all_timestamps.update(timestamps)

    if not all_timestamps:
        return []

    # Sort timestamps for grouping
    sorted_timestamps = sorted(all_timestamps)

    # Group timestamps that fall within the time window
    timestamp_groups: list[list[datetime]] = []
    current_group: list[datetime] = [sorted_timestamps[0]]

    for ts in sorted_timestamps[1:]:
        if ts - current_group[0] <= time_window:
            current_group.append(ts)
        else:
            timestamp_groups.append(current_group)
            current_group = [ts]
    timestamp_groups.append(current_group)

    # Classify each timestamp group
    results: list[dict] = []
    for group in timestamp_groups:
        representative_ts = group[0]

        # Find which stations have anomalies in this time window
        affected_stations = []
        for station_name, timestamps in station_anomalies.items():
            for ts in timestamps:
                if any(abs((ts - g).total_seconds()) <= time_window.total_seconds() for g in group):
                    affected_stations.append(station_name)
                    break

        # Calculate percentage of stations affected
        percent_affected = (len(affected_stations) / total_stations) * 100

        # Classify: weather event if >= threshold, sensor issue otherwise
        classification = "weather_event" if percent_affected >= threshold_percent else "sensor_issue"

        results.append({
            "timestamp": representative_ts,
            "classification": classification,
            "affected_stations": affected_stations,
            "stations_affected": f"{len(affected_stations)}/{total_stations}",
        })

    return results


def render_comparison_tab(
    station_names: list[str],
    station_ids: list[int],
    param_id: int,
    param_name: str,
    param_display_name: str,
):
    """Render the comparison view tab."""
    if len(station_names) < 2:
        st.warning("Select at least 2 stations in the sidebar to use comparison view.")
        return

    st.subheader(f"Station Comparison: {param_display_name}")

    # Fetch data for all selected stations
    all_data: dict[str, dict] = {}
    with st.spinner("Fetching data for comparison..."):
        for name, sid in zip(station_names, station_ids):
            obs = fetch_observations(sid, param_id)
            if obs and obs.observations:
                analysis = analyze_quality(obs, param_name)
                all_data[name] = analysis

    if len(all_data) < 2:
        st.warning("Could not fetch data for enough stations to compare.")
        return

    # Create overlay plot - all stations on one chart
    fig = go.Figure()
    colors = px.colors.qualitative.Set2

    for i, (station_name, analysis) in enumerate(all_data.items()):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=analysis["timestamps"],
            y=analysis["values"],
            mode="lines",
            name=station_name,
            line={"color": color, "width": 2},
            opacity=0.8,
        ))

        # Add anomaly markers for this station
        anomaly_times = {a.timestamp for a in analysis["anomalies"]}
        anomaly_vals = [
            v for t, v in zip(analysis["timestamps"], analysis["values"])
            if t in anomaly_times
        ]
        anomaly_ts = [t for t in analysis["timestamps"] if t in anomaly_times]

        if anomaly_ts:
            fig.add_trace(go.Scatter(
                x=anomaly_ts,
                y=anomaly_vals,
                mode="markers",
                name=f"{station_name} anomalies",
                marker={"color": color, "size": 12, "symbol": "x", "line": {"width": 2}},
                showlegend=False,
            ))

    fig.update_layout(
        title="Side-by-Side Station Comparison",
        xaxis_title="Time",
        yaxis_title=param_display_name,
        hovermode="x unified",
        height=500,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary statistics table
    st.markdown("### Quality Score Comparison")
    summary_data = []
    for station_name, analysis in all_data.items():
        score = analysis["quality_score"]
        summary_data.append({
            "Station": station_name,
            "Quality Score": f"{score.overall:.0f}",
            "Grade": score.grade,
            "Completeness": f"{analysis['completeness'].completeness_percent:.1f}%",
            "Anomalies": len(analysis["anomalies"]),
            "Observations": len(analysis["values"]),
        })

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Cross-station anomaly analysis
    st.markdown("### Cross-Station Anomaly Analysis")

    station_anomalies = {
        name: {a.timestamp for a in analysis["anomalies"]}
        for name, analysis in all_data.items()
    }

    # Collect anomaly classifications
    classified = classify_anomaly_scope(station_anomalies)

    if classified is None:
        st.info(
            "Anomaly classification not yet implemented. "
            "This feature would identify whether anomalies are sensor issues "
            "(appear at only one station) or real weather events (appear at multiple stations)."
        )
    else:
        sensor_issues = [c for c in classified if c["classification"] == "sensor_issue"]
        weather_events = [c for c in classified if c["classification"] == "weather_event"]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Likely Sensor Issues", len(sensor_issues))
        with col2:
            st.metric("Likely Weather Events", len(weather_events))

        if classified:
            class_df = pd.DataFrame(classified)
            st.dataframe(class_df, use_container_width=True, hide_index=True)


def render_quality_report_tab(analysis: dict, station_name: str, station_id: int, param_id: int):
    """Render the quality report tab."""
    st.subheader("Data Quality Details")

    # Completeness section
    st.markdown("### Completeness Analysis")
    comp = analysis["completeness"]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Expected Observations", comp.total_expected)
    with col2:
        st.metric("Present Observations", comp.total_present)
    with col3:
        status = "✅ Pass" if comp.passes_threshold else "❌ Fail"
        st.metric("Threshold Check", status)

    if comp.gaps:
        st.markdown("#### Detected Gaps")
        gaps_df = pd.DataFrame([
            {
                "Start": g.start,
                "End": g.end,
                "Duration": str(g.duration),
                "Missing Count": g.missing_count,
            }
            for g in comp.gaps
        ])
        st.dataframe(gaps_df, use_container_width=True)

    # Range validation section
    st.markdown("### Range Validation")
    range_summary = analysis["range_summary"]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("OK Values", range_summary["ok"], delta=None)
    with col2:
        st.metric("Warnings", range_summary["warning"], delta=None)
    with col3:
        st.metric("Critical", range_summary["critical"], delta=None)

    # Anomalies section
    st.markdown("### Detected Anomalies")
    if analysis["anomalies"]:
        anomalies_df = pd.DataFrame([
            {
                "Timestamp": a.timestamp,
                "Value": a.value,
                "Method": a.method.value,
                "Severity": a.severity.value,
                "Deviation": f"{a.deviation:.2f}",
            }
            for a in analysis["anomalies"]
        ])
        st.dataframe(anomalies_df, use_container_width=True)
    else:
        st.success("No anomalies detected!")


def main():
    """Main dashboard entry point."""
    st.title("SMHI Data Quality Monitor")
    st.markdown(
        "Real-time environmental data quality monitoring using QA engineering principles"
    )

    # Sidebar
    (
        station_id,
        station_name,
        param_id,
        param_display_name,
        comparison_stations,
        comparison_station_ids,
    ) = render_sidebar()
    param_name = PARAM_NAMES.get(param_id, "unknown")

    # Fetch data for primary station
    with st.spinner("Fetching data from SMHI API..."):
        observations = fetch_observations(station_id, param_id)

    if not observations or not observations.observations:
        st.warning("No data available for the selected station and parameter.")
        st.stop()

    # Analyze quality
    with st.spinner("Analyzing data quality..."):
        analysis = analyze_quality(observations, param_name)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "📈 Time Series",
        "📋 Quality Report",
        "🔀 Comparison",
    ])

    with tab1:
        render_overview_tab(analysis, station_name, param_display_name)

    with tab2:
        render_timeseries_tab(analysis, param_display_name)

    with tab3:
        render_quality_report_tab(analysis, station_name, station_id, param_id)

    with tab4:
        render_comparison_tab(
            comparison_stations,
            comparison_station_ids,
            param_id,
            param_name,
            param_display_name,
        )


if __name__ == "__main__":
    main()
