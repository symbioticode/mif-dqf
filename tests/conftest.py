"""
Pytest fixtures for DQF tests

Provides reusable test data and utilities.
"""

from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture
def clean_ohlcv_data():
    """
    Clean OHLCV data fixture (10 days, daily).

     v1.0.0: Added timezone-aware index (UTC)

    Returns:
        pd.DataFrame with clean OHLCV data
    """
    #  FIX: Add tz="UTC" for v1.0.0 compatibility
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")

    data = {
        "open": [100.0 + i for i in range(10)],
        "high": [105.0 + i for i in range(10)],
        "low": [95.0 + i for i in range(10)],
        "close": [102.0 + i for i in range(10)],
        "volume": [1000000 + i * 10000 for i in range(10)],
    }

    df = pd.DataFrame(data, index=dates)
    df.index.name = "date"

    return df


@pytest.fixture
def data_with_large_gap():
    """
    OHLCV data with a large gap (60 days).

     v1.0.0: Added timezone-aware index (UTC)

    Returns:
        pd.DataFrame with gap in dates
    """
    # First 5 days
    #  FIX: Add tz="UTC"
    dates1 = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")

    # Skip 60 days, then 5 more days
    dates2 = pd.date_range("2024-03-15", periods=5, freq="D", tz="UTC")

    #  FIX: Use pd.concat instead of deprecated append
    dates = pd.DatetimeIndex(list(dates1) + list(dates2))

    data = {
        "open": list(range(10)),
        "high": list(range(10, 20)),
        "low": list(range(-10, 0)),
        "close": list(range(5, 15)),
        "volume": [1000] * 10,
    }

    df = pd.DataFrame(data, index=dates)
    df.index.name = "date"

    return df


@pytest.fixture
def minimal_metadata():
    """
    Minimal metadata fixture.

    Returns:
        Dict with minimal metadata
    """
    return {"download_timestamp": datetime.now().isoformat(), "source_version": "v1.0"}


@pytest.fixture
def empty_dataframe():
    """
    Empty DataFrame fixture.

    Returns:
        Empty pd.DataFrame
    """
    return pd.DataFrame()


@pytest.fixture
def sample_config_dict():
    """
    Sample configuration dictionary.

    Returns:
        Dict representing DQF config
    """
    return {
        "dqf_version": "4.8",
        "source_uniqueness": {"enabled": True, "require_metadata": False},
        "ohlcv_integrity": {"enabled": True, "max_violation_rate": 0.01},
        "output": {
            "log_dir": "_work/dqf/logs",
            "provenance_dir": "_work/dqf/provenance",
            "report_dir": "_work/dqf/reports",
        },
    }
