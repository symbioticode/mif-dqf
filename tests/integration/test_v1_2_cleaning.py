"""
Integration tests for DQF v1.2 Active Cleaning (cleaning log).

Tests cover:
  1. enable_cleaning_log=False (default) → report.has_cleaning_log is False
  2. enable_cleaning_log=True, clean data → has_cleaning_log is False (no entries)
  3. enable_cleaning_log=True, ffill data → has_cleaning_log is True
  4. get_cleaning_log_df() returns DataFrame with correct columns
  5. get_cleaning_log_df() returns None when no log present
  6. C4 entries have check_id="C4" and intervention="forward_fill"
  7. C3 entries present when weekend bars detected (DIAGNOSTIC mode)
  8. manifest["provenance"]["cleaning_log_uri"] is None when no log
  9. manifest["provenance"]["cleaning_log_uri"] starts with "embedded:sha256:" when log present
  10. manifest["cleaning_log"] is base64 string when log present; absent otherwise
"""

import pandas as pd
import pytest

from dqf.core.config import DQFConfig
from dqf.core.enums import DQFMode
from dqf.core.validator import DQFValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_nyse_df(n: int = 10) -> pd.DataFrame:
    """Well-formed NYSE weekday data (no weekend bars, no ffill, no violations)."""
    # Jan 2–12 2024: Mon–Fri only (skip weekends)
    dates = pd.bdate_range("2024-01-02", periods=n, tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n)],
            "high": [105.0 + i for i in range(n)],
            "low": [95.0 + i for i in range(n)],
            "close": [102.0 + i for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )


def _ffill_df() -> pd.DataFrame:
    """DataFrame with forward-fill sequences in close column (4 consecutive equal values)."""
    dates = pd.bdate_range("2024-01-02", periods=8, tz="UTC")
    close = [100.0, 101.0, 101.0, 101.0, 101.0, 102.0, 103.0, 104.0]  # 3 ffill rows
    return pd.DataFrame(
        {
            "open": [100.0] * 8,
            "high": [110.0] * 8,
            "low": [90.0] * 8,
            "close": close,
            "volume": [1_000_000] * 8,
        },
        index=dates,
    )


def _weekend_df() -> pd.DataFrame:
    """DataFrame that includes Saturday/Sunday bars (distinct values to avoid C4 trigger)."""
    # Jan 2–8 2024 (includes Sat 6 and Sun 7)
    dates = pd.date_range("2024-01-02", periods=7, freq="D", tz="UTC")
    n = len(dates)
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n)],
            "high": [105.0 + i for i in range(n)],
            "low": [95.0 + i for i in range(n)],
            "close": [102.0 + i for i in range(n)],
            "volume": [1_000_000 + i * 10_000 for i in range(n)],
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCleaningLogDisabled:
    def test_default_no_log(self):
        """enable_cleaning_log defaults to False — no log in report."""
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_clean_nyse_df())
        assert report.has_cleaning_log is False

    def test_explicit_false_no_log(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_clean_nyse_df(), enable_cleaning_log=False)
        assert report.has_cleaning_log is False

    def test_get_cleaning_log_df_returns_none_when_disabled(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_clean_nyse_df())
        assert report.get_cleaning_log_df() is None

    def test_cleaning_log_uri_is_none_when_disabled(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_clean_nyse_df())
        assert report.manifest["provenance"]["cleaning_log_uri"] is None

    def test_cleaning_log_key_absent_from_manifest_when_disabled(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_clean_nyse_df())
        assert "cleaning_log" not in report.manifest


class TestCleaningLogEnabled:
    def test_clean_data_no_log_embedded(self):
        """Clean data → no interventions → no log bytes → has_cleaning_log False."""
        config = DQFConfig(mode=DQFMode.CERTIFICATION)
        report = DQFValidator(config).validate(
            _clean_nyse_df(), calendar="NYSE", enable_cleaning_log=True
        )
        assert report.has_cleaning_log is False

    def test_ffill_data_log_embedded(self):
        """Forward-fill data → C4 entries → log embedded."""
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        assert report.has_cleaning_log is True

    def test_log_df_has_correct_columns(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        df = report.get_cleaning_log_df()
        expected = {"row_index", "check_id", "intervention", "field",
                    "value_before", "value_after", "gravity"}
        assert set(df.columns) == expected

    def test_ffill_entries_have_correct_check_id(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        df = report.get_cleaning_log_df()
        c4_rows = df[df["check_id"] == "C4"]
        assert len(c4_rows) > 0

    def test_ffill_entries_intervention_is_forward_fill(self):
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        df = report.get_cleaning_log_df()
        assert (df[df["check_id"] == "C4"]["intervention"] == "forward_fill").all()

    def test_cleaning_log_uri_embedded_prefix(self):
        """cleaning_log_uri should start with 'embedded:sha256:' when log present."""
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        uri = report.manifest["provenance"]["cleaning_log_uri"]
        assert uri is not None
        assert uri.startswith("embedded:sha256:")

    def test_manifest_cleaning_log_is_base64_string(self):
        """manifest['cleaning_log'] must be a base64-decodable ASCII string."""
        import base64
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(_ffill_df(), enable_cleaning_log=True)
        assert "cleaning_log" in report.manifest
        raw = base64.b64decode(report.manifest["cleaning_log"])
        assert isinstance(raw, bytes) and len(raw) > 0

    def test_weekend_bars_c3_entries(self):
        """Weekend bars with explicit NYSE calendar produce C3 calendar_removal entries."""
        # DIAGNOSTIC mode + explicit NYSE calendar → C3 validates against NYSE,
        # detects Sat/Sun bars, emits calendar_removal cleaning entries.
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        report = DQFValidator(config).validate(
            _weekend_df(), calendar="NYSE", enable_cleaning_log=True
        )
        assert report.has_cleaning_log is True
        df = report.get_cleaning_log_df()
        c3_rows = df[df["check_id"] == "C3"]
        assert len(c3_rows) == 2  # Sat Jan 6 + Sun Jan 7
        assert (c3_rows["intervention"] == "calendar_removal").all()
        assert ((c3_rows["gravity"] - 0.2).abs() < 1e-6).all()
