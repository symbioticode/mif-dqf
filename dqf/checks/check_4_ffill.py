"""
Check 4: Forward Fill Detection

Detects excessive forward-fill sequences in price data.
"""

from typing import Any

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
)
from dqf.utils.mpi import InterventionLog


class ForwardFillCheck(BaseCheck):
    """
    Check 4: Forward Fill Detection.

    Detects sequences of identical consecutive values (potential forward-fill).
    """

    def __init__(self) -> None:
        """Initialize Forward Fill check."""
        super().__init__(check_id="check_4_ffill", check_name="Forward Fill Detection")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Run forward-fill detection check.

        Args:
            data: DataFrame with OHLCV data
            symbol: Optional symbol identifier
            source: Optional data source
            metadata: Optional metadata dict
            **kwargs: Additional parameters
                - columns_to_check: list (default ["close"])
                - warn_threshold: int (default 2) - warn if > this
                - max_consecutive_ffill: int (default 3) - fail if > this

        Returns:
            CheckResult with forward-fill detection
        """
        try:
            self._validate_dataframe(data)

            columns_to_check = kwargs.get("columns_to_check", ["close"])
            warn_threshold = kwargs.get("warn_threshold", 2)
            max_consecutive_ffill = kwargs.get("max_consecutive_ffill", 3)

            # Normalize column names
            col_map = {col.lower(): col for col in data.columns}
            check_lower = [c.lower() for c in columns_to_check]

            # Check for missing columns
            missing = [c for c in check_lower if c not in col_map]
            if missing:
                return self._create_result(
                    status=STATUS_ERROR,
                    severity=SEVERITY_CRITICAL,
                    message=f"Missing columns for ffill check: {missing}",
                    details={
                        "missing_columns": missing,
                        "columns_to_check": columns_to_check,
                        "available_columns": list(data.columns),
                    },
                )

            # Map to actual column names
            columns_actual = [col_map[c] for c in check_lower]

            # Initialize details with ffill_sequences structure
            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "columns_checked": columns_to_check,
                "ffill_sequences": {},  #  Required structure
                "max_consecutive_overall": 0,
                "total_ffill_rows": 0,
            }

            max_consecutive_found = 0
            total_ffill_rows = 0
            cleaning_entries: list[dict] = []

            # Analyze each column
            for col_name, col_actual in zip(check_lower, columns_actual, strict=True):
                series = data[col_actual]

                # Skip if all NaN
                if series.isna().all():
                    continue

                # Detect sequences of identical consecutive values
                # A sequence of N identical values = (N-1) forward fills
                is_same_as_prev = series == series.shift(1)

                # Group consecutive True values
                groups = (~is_same_as_prev).cumsum()

                # Count sequence lengths (excluding NaN comparisons)
                sequence_lengths = is_same_as_prev.groupby(groups).sum()

                # Filter to only sequences (length > 0)
                ffill_sequences = sequence_lengths[sequence_lengths > 0]

                if not ffill_sequences.empty:
                    max_seq = int(ffill_sequences.max())
                    total_seq = int(ffill_sequences.sum())
                    seq_count = len(ffill_sequences)

                    #  Store per-column details in expected structure
                    details["ffill_sequences"][col_name] = {
                        "max_consecutive": max_seq,
                        "total_ffill_rows": total_seq,
                        "sequence_count": seq_count,
                    }

                    max_consecutive_found = max(max_consecutive_found, max_seq)
                    total_ffill_rows += total_seq

                    # Cleaning entries: one per row identified as forward fill
                    ffill_mask = is_same_as_prev & ~series.isna()
                    for idx in data.index[ffill_mask]:
                        cleaning_entries.append({
                            "row_index": str(idx),
                            "check_id": "C4",
                            "intervention": "forward_fill",
                            "field": col_name,
                            "value_before": float(series.loc[idx]),
                            "value_after": None,
                            "gravity": 0.5,
                        })

            # Update overall stats
            details["max_consecutive_overall"] = max_consecutive_found
            details["total_ffill_rows"] = total_ffill_rows

            # Interventions: total ffill values that would need to be recovered
            # (emitted regardless of threshold — MPI counts all interventions)
            log = InterventionLog(forward_fills=total_ffill_rows)

            # Determine status based on thresholds
            if max_consecutive_found > max_consecutive_ffill:
                result = self._create_result(
                    status=STATUS_FAIL,
                    severity=SEVERITY_ERROR,
                    message=f"Excessive forward-fill detected: {max_consecutive_found} consecutive (max: {max_consecutive_ffill})",
                    details=details,
                )
                result.interventions = log
                result.cleaning_entries = cleaning_entries
                return result

            if max_consecutive_found > warn_threshold:
                result = self._create_result(
                    status=STATUS_WARN,
                    severity=SEVERITY_WARNING,
                    message=f"Forward-fill sequences detected: max {max_consecutive_found} consecutive (threshold: {warn_threshold})",
                    details=details,
                )
                result.interventions = log
                result.cleaning_entries = cleaning_entries
                return result

            # All clear
            result = self._create_result(
                status=STATUS_PASS,
                severity=SEVERITY_INFO,
                message="No excessive forward-fill detected",
                details=details,
            )
            result.interventions = log
            result.cleaning_entries = cleaning_entries
            return result

        except Exception as e:
            return self._create_result(
                status=STATUS_ERROR,
                severity=SEVERITY_CRITICAL,
                message=f"Forward-fill check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
            )
