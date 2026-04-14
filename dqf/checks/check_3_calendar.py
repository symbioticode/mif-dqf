"""
Check 3: Calendar Alignment — DQF v1.1

Validates that OHLCV data conforms to the declared trading calendar.

Behaviour differs by DQFMode (spec §4 C3):

CERTIFICATION mode:
  - The ``calendar`` kwarg MUST be explicitly provided.
  - Accepted values: NYSE, LSE, EURONEXT, CRYPTO_247, FOREX_245.
  - Missing calendar → FAIL with ERROR_MISSING_METADATA (no fallback).
  - Data is validated against the declared calendar.

DIAGNOSTIC mode:
  - Calendar auto-detection is permitted (existing heuristics).
  - Result carries calendar_source: "INFERRED_CALENDAR" in details.
  - Non-blocking warnings for calendar anomalies.

In both modes:
  - Bars falling outside the declared (or inferred) calendar are counted
    as calendar_removal interventions for MPI computation.
"""

from typing import Any, Optional

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult
from dqf.core.enums import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STATUS_ERROR,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_WARN,
    DQFMode,
)
from dqf.utils.calendar import detect_calendar, is_weekend
from dqf.utils.mpi import InterventionLog

# Calendars accepted in CERTIFICATION mode (spec §4 C3)
ACCEPTED_CALENDARS = frozenset({"NYSE", "LSE", "EURONEXT", "CRYPTO_247", "FOREX_245"})

# Calendars for which weekend bars are off-calendar (i.e. should be removed)
WEEKDAY_ONLY_CALENDARS = frozenset({"NYSE", "LSE", "EURONEXT", "FOREX_245"})


class CalendarAlignmentCheck(BaseCheck):
    """
    Check 3: Calendar Alignment.

    CORE check — failure in CERTIFICATION mode triggers VOID overall status.
    """

    def __init__(self) -> None:
        super().__init__(check_id="check_3_calendar", check_name="Calendar Alignment")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Execute calendar alignment validation.

        Args:
            data: DataFrame to validate (must have DatetimeIndex).
            symbol: Asset symbol (used for auto-detection in DIAGNOSTIC).
            source: Data source identifier.
            metadata: Optional metadata dict.
            **kwargs:
                mode     : DQFMode — defaults to DIAGNOSTIC for backwards compat.
                calendar : str | None — declared calendar name. Required in
                           CERTIFICATION mode.
                require_timezone : bool (default True)
                allow_weekends   : bool (default False)

        Returns:
            CheckResult with PASS, WARN, FAIL or ERROR status.
        """
        try:
            self._validate_dataframe(data)
            self._validate_datetime_index(data)

            mode: DQFMode = kwargs.get("mode", DQFMode.DIAGNOSTIC)  # Session 4 rewrite
            calendar: Optional[str] = kwargs.get("calendar", None)
            require_timezone: bool = kwargs.get("require_timezone", True)
            allow_weekends: bool = kwargs.get("allow_weekends", False)

            details: dict[str, Any] = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "mode": mode.value,
            }

            # ------------------------------------------------------------------
            # Timezone check (both modes)
            # ------------------------------------------------------------------
            if require_timezone and data.index.tz is None:
                return self._create_result(
                    status=STATUS_FAIL,
                    severity=SEVERITY_ERROR,
                    message="Index is not timezone-aware",
                    details=details,
                )
            if data.index.tz is not None:
                details["timezone"] = str(data.index.tz)

            # ------------------------------------------------------------------
            # Duplicate timestamps (both modes)
            # ------------------------------------------------------------------
            duplicates = int(data.index.duplicated().sum())
            if duplicates > 0:
                details["duplicate_timestamps"] = duplicates
                return self._create_result(
                    status=STATUS_FAIL,
                    severity=SEVERITY_ERROR,
                    message=f"Found {duplicates} duplicate timestamps",
                    details=details,
                )

            # ------------------------------------------------------------------
            # Mode bifurcation: determine effective calendar
            # ------------------------------------------------------------------
            if mode == DQFMode.CERTIFICATION:
                return self._run_certification(data, calendar, details, allow_weekends)
            else:
                return self._run_diagnostic(data, symbol, calendar, details, allow_weekends)

        except Exception as e:
            return self._create_result(
                status=STATUS_ERROR,
                severity=SEVERITY_CRITICAL,
                message=f"Calendar check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
            )

    # ------------------------------------------------------------------
    # CERTIFICATION path
    # ------------------------------------------------------------------

    def _run_certification(
        self,
        data: pd.DataFrame,
        calendar: Optional[str],
        details: dict,
        allow_weekends: bool,
    ) -> CheckResult:
        """Strict validation — calendar must be declared, no auto-detection."""
        if calendar is None:
            return self._create_result(
                status=STATUS_FAIL,
                severity=SEVERITY_CRITICAL,
                message=(
                    "ERROR_MISSING_METADATA: calendar must be explicitly declared "
                    "in CERTIFICATION mode. "
                    f"Accepted: {', '.join(sorted(ACCEPTED_CALENDARS))}"
                ),
                details=details,
            )

        cal_upper = calendar.upper()
        if cal_upper not in ACCEPTED_CALENDARS:
            return self._create_result(
                status=STATUS_FAIL,
                severity=SEVERITY_ERROR,
                message=(
                    f"Unknown calendar '{calendar}'. "
                    f"Accepted: {', '.join(sorted(ACCEPTED_CALENDARS))}"
                ),
                details=details,
            )

        details["calendar"] = cal_upper
        details["calendar_source"] = "DECLARED"
        return self._validate_against_calendar(data, cal_upper, details, allow_weekends)

    # ------------------------------------------------------------------
    # DIAGNOSTIC path
    # ------------------------------------------------------------------

    def _run_diagnostic(
        self,
        data: pd.DataFrame,
        symbol: Optional[str],
        calendar: Optional[str],
        details: dict,
        allow_weekends: bool,
    ) -> CheckResult:
        """Permissive validation — auto-detection allowed."""
        if calendar is not None and calendar.upper() in ACCEPTED_CALENDARS:
            effective_calendar = calendar.upper()
            details["calendar_source"] = "DECLARED"
        else:
            # Auto-detect from symbol or data patterns
            if symbol:
                detected = detect_calendar(symbol, data)
            else:
                has_weekends = any(is_weekend(dt) for dt in data.index)
                detected = "CRYPTO_247" if has_weekends else "NYSE"

            effective_calendar = detected.upper() if detected != "UNKNOWN" else "NYSE"
            details["calendar_source"] = "INFERRED_CALENDAR"
            details["detected_calendar"] = effective_calendar

        details["calendar"] = effective_calendar

        result = self._validate_against_calendar(data, effective_calendar, details, allow_weekends)

        # Tag DIAGNOSTIC results so consumers know this is not a certified run
        if result.details is not None:
            result.details["mode_annotation"] = "DIAGNOSTIC — not eligible for MIF certification"
        return result

    # ------------------------------------------------------------------
    # Core validation logic (shared)
    # ------------------------------------------------------------------

    def _validate_against_calendar(
        self,
        data: pd.DataFrame,
        calendar: str,
        details: dict,
        allow_weekends: bool,
    ) -> CheckResult:
        """
        Validate data against the given calendar and emit interventions.

        For weekday-only calendars (NYSE, LSE, EURONEXT, FOREX_245), bars on
        weekends are counted as calendar_removal interventions.
        """
        issues = []
        off_calendar_count = 0

        # Weekend check for weekday-only calendars
        if calendar in WEEKDAY_ONLY_CALENDARS and not allow_weekends:
            weekend_bars = [dt for dt in data.index if is_weekend(dt)]
            off_calendar_count = len(weekend_bars)
            if off_calendar_count > 0:
                details["weekend_bars"] = off_calendar_count
                issues.append(f"{off_calendar_count} weekend bar(s) outside {calendar} calendar")

        details["off_calendar_bars"] = off_calendar_count

        # Frequency check (informational)
        if len(data) > 1:
            freq = pd.infer_freq(data.index)
            details["inferred_frequency"] = freq
            if freq is None:
                issues.append("Could not infer regular frequency")

        # Interventions: bars that would be removed to produce a canonical dataset
        log = InterventionLog(calendar_removals=off_calendar_count)

        if issues:
            result = self._create_result(
                status=STATUS_WARN,
                severity=SEVERITY_WARNING,
                message=f"Calendar alignment issues: {'; '.join(issues)}",
                details=details,
            )
        else:
            result = self._create_result(
                status=STATUS_PASS,
                severity=SEVERITY_INFO,
                message=f"Calendar alignment validated ({calendar})",
                details=details,
            )

        result.interventions = log
        return result
