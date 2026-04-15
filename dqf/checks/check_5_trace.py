"""
Check 5: Index Traceability.

Validates index structure and chronological ordering.
"""

from typing import Any

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult


class IndexTraceabilityCheck(BaseCheck):
    """
    Check 5: Index Traceability.

    Validates that:
    - Index is unique (no duplicates)
    - Index is chronological (sorted)
    - Index is timezone-aware
    - Index is properly formatted
    """

    def __init__(self) -> None:
        """Initialize Index Traceability check."""
        super().__init__(check_id="check_5_trace", check_name="Index Traceability")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CheckResult:
        """
        Execute index traceability validation.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - require_unique: bool (default: True)
                - require_chronological: bool (default: True)
                - require_timezone: bool (default: True)

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)
            self._validate_datetime_index(data)

            # Extract config
            require_unique = kwargs.get("require_unique", True)
            require_chronological = kwargs.get("require_chronological", True)
            require_timezone = kwargs.get("require_timezone", True)

            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "index_type": str(type(data.index).__name__),
            }

            issues = []

            # Check 1: Index uniqueness
            duplicates = data.index.duplicated().sum()
            details["duplicate_count"] = int(duplicates)

            if duplicates > 0:
                if require_unique:
                    return self._create_fail_result(
                        message=f"Found {duplicates} duplicate index entries",
                        severity="ERROR",
                        details=details,
                    )
                else:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {duplicates} duplicate index entries",
                        }
                    )

            # Check 2: Chronological order
            is_sorted = data.index.is_monotonic_increasing
            details["is_sorted"] = is_sorted

            if not is_sorted:
                if require_chronological:
                    return self._create_fail_result(
                        message="Index is not chronologically sorted",
                        severity="ERROR",
                        details=details,
                    )
                else:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": "Index is not chronologically sorted",
                        }
                    )

            # Check 3: Timezone awareness
            has_timezone = data.index.tz is not None
            details["has_timezone"] = has_timezone

            if has_timezone:
                details["timezone"] = str(data.index.tz)

            if not has_timezone:
                if require_timezone:
                    return self._create_fail_result(
                        message="Index is not timezone-aware",
                        severity="ERROR",
                        details=details,
                    )
                else:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": "Index is not timezone-aware",
                        }
                    )

            # Check 4: Index frequency
            if len(data) > 1:
                freq = pd.infer_freq(data.index)
                details["inferred_frequency"] = freq

                if freq is None:
                    issues.append(
                        {
                            "severity": "INFO",
                            "message": "Could not infer regular frequency",
                        }
                    )

            # Check 5: Index range
            details["start_date"] = str(data.index.min())
            details["end_date"] = str(data.index.max())
            details["time_span_days"] = (data.index.max() - data.index.min()).days

            # Determine result
            if issues:
                return self._create_warning_result(
                    message=f"Index traceability passed with {len(issues)} warnings",
                    details={**details, "warnings": issues},
                )

            return self._create_pass_result(
                message="Index traceability validated successfully",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Index traceability check failed: {str(e)}",
                exception=e,
            )
