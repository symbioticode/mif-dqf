"""
Check 6: Sanity Tests.

Statistical and logical sanity checks on OHLCV data.
"""

from typing import Any

import numpy as np
import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult


class SanityTestsCheck(BaseCheck):
    """
    Check 6: Sanity Tests.

    Validates that:
    - Returns are within reasonable bounds
    - No extreme outliers
    - Volume patterns are reasonable
    - Prices are positive and realistic
    """

    def __init__(self) -> None:
        """Initialize Sanity Tests check."""
        super().__init__(check_id="check_6_sanity", check_name="Sanity Tests")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Execute sanity tests validation.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - extreme_return_threshold: float (default: 1.0, i.e., 100%)
                - zero_volume_days: int (default: 5)
                - volatility_multiplier: float (default: 5.0)
                - min_price: float (default: 1e-8)

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)

            # Extract config
            extreme_return_threshold = kwargs.get("extreme_return_threshold", 1.0)
            zero_volume_days = kwargs.get("zero_volume_days", 5)
            volatility_multiplier = kwargs.get("volatility_multiplier", 5.0)
            min_price = kwargs.get("min_price", 1e-8)

            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "anomalies_count": 0,  # Initialize to 0, increment below
            }

            issues = []

            # Check 1: Extreme returns
            if "close" in data.columns:
                returns = data["close"].pct_change()
                extreme_returns = (returns.abs() > extreme_return_threshold).sum()

                details["extreme_returns"] = int(extreme_returns)

                if extreme_returns > 0:
                    max_return = float(returns.abs().max())
                    details["max_return"] = max_return

                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {extreme_returns} extreme returns (>{extreme_return_threshold:.0%})",
                        }
                    )

            # Check 2: Zero volume days
            if "volume" in data.columns:
                zero_vol = (data["volume"] == 0).sum()
                details["zero_volume_days"] = int(zero_vol)

                if zero_vol > zero_volume_days:
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {zero_vol} zero-volume days (threshold: {zero_volume_days})",
                        }
                    )

            # Check 3: Price outliers (using IQR method)
            if "close" in data.columns:
                q1 = data["close"].quantile(0.25)
                q3 = data["close"].quantile(0.75)
                iqr = q3 - q1

                lower_bound = q1 - volatility_multiplier * iqr
                upper_bound = q3 + volatility_multiplier * iqr

                outliers = ((data["close"] < lower_bound) | (data["close"] > upper_bound)).sum()
                details["price_outliers"] = int(outliers)

                if outliers > 0:
                    issues.append(
                        {
                            "severity": "INFO",
                            "message": f"Found {outliers} price outliers (IQR method)",
                        }
                    )

            # Check 4: Minimum price threshold
            price_cols = [c for c in ["open", "high", "low", "close"] if c in data.columns]
            for col in price_cols:
                too_low = (data[col] < min_price).sum()
                if too_low > 0:
                    details[f"{col}_too_low"] = int(too_low)
                    issues.append(
                        {
                            "severity": "WARNING",
                            "message": f"Found {too_low} {col} values below {min_price}",
                        }
                    )

            # Check 5: NaN/Inf detection
            nan_count = data.isna().sum().sum()
            inf_count = np.isinf(data.select_dtypes(include=[np.number])).sum().sum()

            details["nan_count"] = int(nan_count)
            details["inf_count"] = int(inf_count)

            if nan_count > 0:
                return self._create_fail_result(
                    message=f"Found {nan_count} NaN values",
                    severity="ERROR",
                    details=details,
                )

            if inf_count > 0:
                return self._create_fail_result(
                    message=f"Found {inf_count} infinite values",
                    severity="ERROR",
                    details=details,
                )

            # Check 6: Volume spikes
            if "volume" in data.columns and len(data) > 1:
                vol_median = data["volume"].median()
                if vol_median > 0:
                    vol_ratio = data["volume"] / vol_median
                    extreme_vol = (vol_ratio > 10).sum()

                    details["volume_spikes"] = int(extreme_vol)

                    if extreme_vol > 0:
                        issues.append(
                            {
                                "severity": "INFO",
                                "message": f"Found {extreme_vol} volume spikes (>10x median)",
                            }
                        )

            # Determine result
            error_issues = [i for i in issues if i["severity"] == "ERROR"]
            if error_issues:
                details["anomalies_count"] = len(error_issues)
                return self._create_fail_result(
                    message=f"Sanity checks failed: {len(error_issues)} errors",
                    severity="ERROR",
                    details={**details, "issues": issues},
                )

            if issues:
                details["anomalies_count"] = len(issues)
                return self._create_warning_result(
                    message=f"Sanity checks passed with {len(issues)} warnings",
                    details={**details, "warnings": issues},
                )

            # anomalies_count already set to 0 at initialization
            return self._create_pass_result(
                message="All sanity checks passed",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Sanity checks failed: {str(e)}",
                exception=e,
            )
