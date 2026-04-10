"""
Check 2: OHLCV Integrity

Validates OHLCV data integrity constraints.
"""

from typing import Any

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult
from dqf.core.enums import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    STATUS_ERROR,
    STATUS_FAIL,
    STATUS_PASS,
)
from dqf.utils.mpi import InterventionLog


class IntegrityCheck(BaseCheck):
    """
    Check 2: OHLCV Integrity.

    Validates:
        - Required columns present
        - High >= Low
        - High >= Open, Close
        - Low <= Open, Close
        - No negative values in OHLC
        - No negative volume
    """

    def __init__(self) -> None:
        """Initialize OHLCV Integrity check."""
        super().__init__(check_id="check_2_integrity", check_name="OHLCV Integrity")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Run OHLCV integrity check.

        Args:
            data: DataFrame with OHLCV data
            symbol: Optional symbol identifier
            source: Optional data source
            metadata: Optional metadata dict
            **kwargs: Additional parameters
                - max_violation_rate: float (default 0.01)
                - required_columns: list (default ["open", "high", "low", "close", "volume"])

        Returns:
            CheckResult with integrity validation
        """
        try:
            self._validate_dataframe(data)

            max_violation_rate = kwargs.get("max_violation_rate", 0.01)
            required_columns = kwargs.get(
                "required_columns", ["open", "high", "low", "close", "volume"]
            )

            # Normalize column names (case-insensitive)
            col_map = {col.lower(): col for col in data.columns}
            required_lower = [c.lower() for c in required_columns]

            # Check for missing columns
            missing = [c for c in required_lower if c not in col_map]
            if missing:
                return self._create_result(
                    status=STATUS_ERROR,
                    severity=SEVERITY_CRITICAL,
                    message=f"Missing required OHLCV columns: {missing}. Found columns: {list(data.columns)}",
                    details={
                        "missing_columns": missing,
                        "found_columns": list(data.columns),
                        "error": f"Missing required OHLCV columns: {missing}. Found columns: {list(data.columns)}",
                        "error_type": "ValueError",
                    },
                )

            # Map required columns to actual column names
            ohlcv = {
                name: col_map[name]
                for name in ["open", "high", "low", "close", "volume"]
                if name in col_map
            }

            # Initialize details with violation_breakdown
            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "violations": {},
                "violation_breakdown": {},  #  Required by tests
                "total_violations": 0,
                "violation_rate": 0.0,
            }

            breakdown = {}

            # Check High >= Low
            if "high" in ohlcv and "low" in ohlcv:
                count = int((data[ohlcv["high"]] < data[ohlcv["low"]]).sum())
                if count > 0:
                    breakdown["high_low"] = count

            # Check High >= Open
            if "high" in ohlcv and "open" in ohlcv:
                count = int((data[ohlcv["high"]] < data[ohlcv["open"]]).sum())
                if count > 0:
                    breakdown["high_open"] = count

            # Check High >= Close
            if "high" in ohlcv and "close" in ohlcv:
                count = int((data[ohlcv["high"]] < data[ohlcv["close"]]).sum())
                if count > 0:
                    breakdown["high_close"] = count

            # Check Low <= Open
            if "low" in ohlcv and "open" in ohlcv:
                count = int((data[ohlcv["low"]] > data[ohlcv["open"]]).sum())
                if count > 0:
                    breakdown["low_open"] = count

            # Check Low <= Close
            if "low" in ohlcv and "close" in ohlcv:
                count = int((data[ohlcv["low"]] > data[ohlcv["close"]]).sum())
                if count > 0:
                    breakdown["low_close"] = count

            # Check for negative values in OHLC
            for col_name in ["open", "high", "low", "close"]:
                if col_name in ohlcv:
                    count = int((data[ohlcv[col_name]] < 0).sum())
                    if count > 0:
                        breakdown[f"negative_{col_name}"] = count

            # Check for negative volume (ignore NaN)
            if "volume" in ohlcv:
                vol_series = data[ohlcv["volume"]]
                count = int(((vol_series < 0) & vol_series.notna()).sum())
                if count > 0:
                    breakdown["negative_volume"] = count

            # Calculate totals
            total_violations = sum(breakdown.values())
            violation_rate = total_violations / len(data) if len(data) > 0 else 0.0

            # Update details
            details["violations"] = breakdown
            details["violation_breakdown"] = breakdown  #  Same as violations for compatibility
            details["total_violations"] = total_violations
            details["violation_rate"] = violation_rate

            # Emit interventions for MPI — physical violations detected
            # (In Phase 1, DQF detects; Phase 2 will actively correct.
            #  The count reflects what would need to be fixed.)
            log = InterventionLog(physical_corrections=total_violations)

            # Determine status
            if violation_rate > max_violation_rate:
                result = self._create_result(
                    status=STATUS_FAIL,
                    severity=SEVERITY_ERROR,
                    message=f"Integrity violations: {violation_rate:.2%} (max: {max_violation_rate:.2%})",
                    details=details,
                )
                result.interventions = log
                return result

            result = self._create_result(
                status=STATUS_PASS,
                severity=SEVERITY_INFO,
                message=(
                    "OHLCV integrity validated successfully"
                    if total_violations == 0
                    else f"OHLCV integrity acceptable: {total_violations} violations ({violation_rate:.2%})"
                ),
                details=details,
            )
            result.interventions = log
            return result

        except Exception as e:
            return self._create_result(
                status=STATUS_ERROR,
                severity=SEVERITY_CRITICAL,
                message=f"Integrity check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
            )
