"""
Check 1: Source Uniqueness.

Validates that data comes from a single, identifiable source.
"""

from typing import Any

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult


class SourceUniquenessCheck(BaseCheck):
    """
    Check 1: Source Uniqueness.

    Validates that:
    - Data has a clearly identified source
    - No mixing of data from different sources
    - Source metadata is consistent
    """

    def __init__(self) -> None:
        """Initialize Source Uniqueness check."""
        super().__init__(check_id="check_1_source", check_name="Source Uniqueness")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CheckResult:
        """
        Execute source uniqueness validation.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - require_metadata: bool (default: False)
                - max_gap_days: int (default: 30)

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)

            # Extract config parameters
            require_metadata = kwargs.get("require_metadata", False)
            max_gap_days = kwargs.get("max_gap_days", 30)

            issues = []
            details: dict[str, Any] = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
            }

            # Check 1: Source identifier provided
            if not source:
                if require_metadata:
                    return self._create_fail_result(
                        message="No source identifier provided",
                        details=details,
                    )
                else:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": "No source identifier provided",
                        }
                    )

            # Check 2: Source in metadata (if metadata provided)
            if metadata:
                metadata_source = metadata.get("source")
                details["metadata_source"] = metadata_source

                if source and metadata_source and source != metadata_source:
                    return self._create_fail_result(
                        message=f"Source mismatch: {source} != {metadata_source}",
                        severity="ERROR",
                        details=details,
                    )

            # Check 3: Data gaps (potential multi-source indicator)
            if isinstance(data.index, pd.DatetimeIndex):
                gaps = data.index.to_series().diff()
                large_gaps = gaps[gaps > pd.Timedelta(days=max_gap_days)]

                if len(large_gaps) > 0:
                    details["large_gaps_count"] = len(large_gaps)
                    details["max_gap_days"] = gaps.max().days if not gaps.empty else 0

                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {len(large_gaps)} gaps > {max_gap_days} days",
                        }
                    )

            # Check 4: Source column in data (if present)
            if "source" in data.columns:
                unique_sources = data["source"].unique()
                details["sources_in_data"] = list(unique_sources)

                if len(unique_sources) > 1:
                    return self._create_fail_result(
                        message=f"Multiple sources in data: {list(unique_sources)}",
                        severity="ERROR",
                        details=details,
                    )

            # Determine final status
            if issues:
                return self._create_warning_result(
                    message=f"Source validation passed with {len(issues)} warnings",
                    details={**details, "warnings": issues},
                )

            return self._create_pass_result(
                message="Source uniqueness validated successfully",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Check execution failed: {str(e)}",
                exception=e,
            )
