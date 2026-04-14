"""
Unit tests for Check 3: Calendar Alignment — DQF v1.1 delta

Tests the v1.1 additions:
  - CERTIFICATION mode: calendar required, ERROR_MISSING_METADATA on missing
  - CERTIFICATION mode: unknown calendar → FAIL
  - CERTIFICATION mode: valid calendar → validated against it
  - DIAGNOSTIC mode: auto-detection permitted, INFERRED_CALENDAR flag
  - DIAGNOSTIC mode: pre-declared calendar accepted
  - Interventions: calendar_removal count for off-calendar bars
  - Weekend bars counted as calendar_removal for weekday-only calendars
  - CRYPTO_247: weekends allowed, zero removals
"""

import pandas as pd
import pytest

from dqf.checks.check_3_calendar import ACCEPTED_CALENDARS, CalendarAlignmentCheck
from dqf.core.enums import STATUS_FAIL, STATUS_PASS, STATUS_WARN, DQFMode

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_nyse_df(periods: int = 10, tz: str = "UTC") -> pd.DataFrame:
    """Weekday-only data aligned with NYSE (no weekends)."""
    dates = pd.bdate_range("2024-01-02", periods=periods, freq="B", tz=tz)
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(len(dates))],
            "high": [105.0 + i for i in range(len(dates))],
            "low": [95.0 + i for i in range(len(dates))],
            "close": [102.0 + i for i in range(len(dates))],
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )


def _make_df_with_weekends(periods: int = 14, tz: str = "UTC") -> pd.DataFrame:
    """Calendar data that includes weekend bars."""
    dates = pd.date_range("2024-01-01", periods=periods, freq="D", tz=tz)
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(len(dates))],
            "high": [105.0 + i for i in range(len(dates))],
            "low": [95.0 + i for i in range(len(dates))],
            "close": [102.0 + i for i in range(len(dates))],
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# CERTIFICATION mode — calendar required
# ---------------------------------------------------------------------------


class TestCertificationMode:
    def test_missing_calendar_returns_fail(self):
        """CERTIFICATION + no calendar → FAIL with ERROR_MISSING_METADATA."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar=None)

        assert result.status == STATUS_FAIL
        assert "ERROR_MISSING_METADATA" in result.message

    def test_missing_calendar_message_lists_accepted(self):
        """Error message must list accepted calendar names."""
        check = CalendarAlignmentCheck()
        result = check.run(data=_make_nyse_df(), mode=DQFMode.CERTIFICATION, calendar=None)

        for cal in ACCEPTED_CALENDARS:
            assert cal in result.message

    def test_unknown_calendar_returns_fail(self):
        """Unrecognised calendar name → FAIL."""
        check = CalendarAlignmentCheck()
        result = check.run(
            data=_make_nyse_df(),
            mode=DQFMode.CERTIFICATION,
            calendar="TOKYO_EXCHANGE",
        )
        assert result.status == STATUS_FAIL

    def test_valid_calendar_nyse_clean_data_passes(self):
        """NYSE calendar + weekday-only data → PASS."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")

        assert result.status == STATUS_PASS

    def test_valid_calendar_nyse_with_weekends_warns(self):
        """NYSE calendar + weekend bars → WARN (off-calendar bars detected)."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")

        assert result.status == STATUS_WARN

    def test_crypto_247_with_weekends_passes(self):
        """CRYPTO_247 allows weekend bars → PASS."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="CRYPTO_247")

        assert result.status == STATUS_PASS

    def test_calendar_stored_in_details(self):
        """Declared calendar must appear in result details."""
        check = CalendarAlignmentCheck()
        result = check.run(data=_make_nyse_df(), mode=DQFMode.CERTIFICATION, calendar="LSE")

        assert result.details.get("calendar") == "LSE"
        assert result.details.get("calendar_source") == "DECLARED"

    @pytest.mark.parametrize("cal", sorted(ACCEPTED_CALENDARS))
    def test_all_accepted_calendars_do_not_fail_on_name(self, cal):
        """Every accepted calendar name must not trigger unknown-calendar FAIL."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar=cal)

        # Result may be PASS or WARN (weekend data for weekday-only cals)
        # but must NOT fail on calendar name validation
        assert "Unknown calendar" not in result.message


# ---------------------------------------------------------------------------
# DIAGNOSTIC mode — auto-detection permitted
# ---------------------------------------------------------------------------


class TestDiagnosticMode:
    def test_no_calendar_auto_detects(self):
        """DIAGNOSTIC + no calendar → auto-detect, result not FAIL."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df, mode=DQFMode.DIAGNOSTIC)

        assert result.status != STATUS_FAIL

    def test_inferred_calendar_flag_set(self):
        """DIAGNOSTIC without calendar must set calendar_source to INFERRED_CALENDAR."""
        check = CalendarAlignmentCheck()
        result = check.run(data=_make_nyse_df(), mode=DQFMode.DIAGNOSTIC)

        assert result.details.get("calendar_source") == "INFERRED_CALENDAR"

    def test_declared_calendar_in_diagnostic_accepted(self):
        """DIAGNOSTIC + valid calendar → treated as declared, not inferred."""
        check = CalendarAlignmentCheck()
        result = check.run(
            data=_make_nyse_df(),
            mode=DQFMode.DIAGNOSTIC,
            calendar="NYSE",
        )
        assert result.details.get("calendar_source") == "DECLARED"

    def test_mode_annotation_in_details(self):
        """DIAGNOSTIC results carry a mode annotation in details."""
        check = CalendarAlignmentCheck()
        result = check.run(data=_make_nyse_df(), mode=DQFMode.DIAGNOSTIC)

        annotation = result.details.get("mode_annotation", "")
        assert "DIAGNOSTIC" in annotation

    def test_default_mode_is_diagnostic(self):
        """Calling run() without mode kwarg defaults to DIAGNOSTIC (backwards compat)."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df)

        assert result.status != STATUS_FAIL


# ---------------------------------------------------------------------------
# Interventions
# ---------------------------------------------------------------------------


class TestCalendarInterventions:
    def test_clean_nyse_data_zero_removals(self):
        """No weekend bars → calendar_removal = 0."""
        check = CalendarAlignmentCheck()
        df = _make_nyse_df()
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")

        assert result.interventions is not None
        assert result.interventions.calendar_removals == 0

    def test_weekend_bars_counted_as_removals(self):
        """Weekend bars in NYSE data → calendar_removal > 0."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends(periods=14)  # 14 days = ~4 weekend bars
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")

        assert result.interventions is not None
        assert result.interventions.calendar_removals > 0

    def test_removal_count_matches_details(self):
        """calendar_removal count matches off_calendar_bars in details."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends(periods=14)
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")

        assert result.interventions.calendar_removals == result.details["off_calendar_bars"]

    def test_crypto_247_zero_removals_with_weekends(self):
        """Weekends allowed for CRYPTO_247 → zero removal interventions."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends(periods=14)
        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="CRYPTO_247")

        assert result.interventions is not None
        assert result.interventions.calendar_removals == 0

    def test_diagnostic_mode_also_emits_interventions(self):
        """Interventions are emitted in DIAGNOSTIC mode too."""
        check = CalendarAlignmentCheck()
        df = _make_df_with_weekends(periods=14)
        result = check.run(data=df, mode=DQFMode.DIAGNOSTIC, calendar="NYSE")

        assert result.interventions is not None


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestCalendarErrorPaths:
    def test_missing_datetime_index_raises_error(self):
        """Non-DatetimeIndex → ERROR result."""
        check = CalendarAlignmentCheck()
        df = pd.DataFrame({"close": [1, 2, 3]}, index=[0, 1, 2])

        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")
        assert result.status in (STATUS_FAIL, "ERROR")

    def test_no_timezone_returns_fail(self):
        """Timezone-naive index → FAIL when require_timezone=True (default)."""
        check = CalendarAlignmentCheck()
        dates = pd.bdate_range("2024-01-02", periods=5, freq="B")  # tz-naive
        df = pd.DataFrame({"close": range(5)}, index=dates)

        result = check.run(data=df, mode=DQFMode.CERTIFICATION, calendar="NYSE")
        assert result.status == STATUS_FAIL
