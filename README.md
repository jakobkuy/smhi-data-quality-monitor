# SMHI Data Quality Monitor

[![CI](https://github.com/jakobkuy/smhi-data-quality-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jakobkuy/smhi-data-quality-monitor/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python-based environmental sensor dashboard that fetches real-time meteorological and hydrological data from SMHI's Open Data APIs, validates data quality using QA engineering patterns, and visualizes results through an interactive Streamlit dashboard.

## Features

- **Real-time data fetching** from SMHI Meteorological and Hydrological APIs
- **Schema validation** using Pydantic models for every API response
- **Range validation** with physics-based plausibility checks
- **Anomaly detection** using Z-score and IQR methods
- **Data quality scoring** (0-100) with weighted components
- **Interactive Streamlit dashboard** with time series visualization
- **Comprehensive test suite** with pytest and mocked API responses
- **CI/CD pipeline** with GitHub Actions, ruff linting, and mypy type checking

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jakobkuy/smhi-data-quality-monitor.git
cd smhi-data-quality-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run dashboard/app.py
```

## Project Structure

```
smhi-data-quality-monitor/
├── src/
│   ├── api/              # SMHI API clients
│   ├── validation/       # Data validation logic
│   ├── quality/          # Quality scoring system
│   └── utils/            # Configuration and logging
├── tests/                # pytest test suite
├── dashboard/            # Streamlit application
└── .github/workflows/    # CI/CD pipeline
```

## Data Sources

This project uses SMHI's (Swedish Meteorological and Hydrological Institute) Open Data APIs:

- **Meteorological Observations**: Temperature, wind speed, precipitation, humidity
- **Hydrological Observations**: Water level, water flow/discharge

Both APIs are public and free to use under the CC BY 4.0 license.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

## QA Philosophy

This project treats environmental sensor data with the same rigor a QA engineer would apply to production software. Every data point is validated against expected schemas, checked for physical plausibility, and analyzed for statistical anomalies. The goal is not just visualization — it's building confidence that the data can be trusted for downstream decisions.

## License

MIT License - see [LICENSE](LICENSE) for details.
