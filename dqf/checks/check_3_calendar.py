"""
Check 3: Calendar Alignment.

Validates calendar consistency and timezone handling.
"""

from typing import Any

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult
from dqf.utils.calendar import detect_calendar, is_weekend


class CalendarAlignmentCheck(BaseCheck):
    """
    Check 3: Calendar Alignment.

    Validates that:
    - Data follows expected trading calendar
    - No data on weekends (unless specified)
    - Timezone is consistent
    - Frequency is regular
    """

    def __init__(self) -> None:
        """Initialize Calendar Alignment check."""
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
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - auto_detect: bool (default: True)
                - require_timezone: bool (default: True)
                - allow_weekends: bool (default: False)

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)
            self._validate_datetime_index(data)

            # Extract config
            auto_detect = kwargs.get("auto_detect", True)
            require_timezone = kwargs.get("require_timezone", True)
            allow_weekends = kwargs.get("allow_weekends", False)

            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
            }

            issues = []

            # Check 1: Timezone awareness
            if require_timezone:
                if data.index.tz is None:
                    return self._create_fail_result(
                        message="Index is not timezone-aware",
                        severity="ERROR",
                        details=details,
                    )
                else:
                    details["timezone"] = str(data.index.tz)

            # Check 2: Weekend data
            if not allow_weekends:
                weekend_count = sum(is_weekend(dt) for dt in data.index)
                if weekend_count > 0:
                    details["weekend_rows"] = weekend_count
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {weekend_count} weekend entries",
                        }
                    )

            # Check 3: Calendar detection
            if auto_detect:
                # detect_calendar expects symbol string, not index
                # Use symbol if provided, otherwise try to detect from data patterns
                if symbol:
                    detected_calendar = detect_calendar(symbol)
                else:
                    # Detect from data patterns (24/7 vs weekdays only)
                    has_weekends = sum(is_weekend(dt) for dt in data.index) > 0
                    detected_calendar = "CRYPTO_24_7" if has_weekends else "NYSE"

                details["detected_calendar"] = detected_calendar

                if detected_calendar == "unknown":
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": "Could not detect trading calendar",
                        }
                    )

            # Check 4: Frequency analysis
            if len(data) > 1:
                freq = pd.infer_freq(data.index)
                details["inferred_frequency"] = freq

                if freq is None:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": "Could not infer regular frequency",
                        }
                    )

            # Check 5: Duplicate timestamps
            duplicates = data.index.duplicated().sum()
            if duplicates > 0:
                details["duplicate_timestamps"] = int(duplicates)
                return self._create_fail_result(
                    message=f"Found {duplicates} duplicate timestamps",
                    severity="ERROR",
                    details=details,
                )

            # Determine result
            if issues:
                return self._create_warning_result(
                    message=f"Calendar alignment passed with {len(issues)} warnings",
                    details={**details, "warnings": issues},
                )

            return self._create_pass_result(
                message="Calendar alignment validated successfully",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Calendar check failed: {str(e)}",
                exception=e,
            )
