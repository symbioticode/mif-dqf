#!/usr/bin/env python3
"""
Example 04: Custom Check Implementation

Demonstrates how to create and register custom validation checks with DQF v1.1+.

Custom checks:
  - Inherit from BaseCheck
  - Implement run(**kwargs) → CheckResult
  - Are registered via validator.add_custom_check(check_id, check)
  - Run as ADVISORY checks (WARN raises status to WARNING, never to VOID)
"""

import os
from typing import Any

import pandas as pd

from dqf import DQFValidator
from dqf.checks.base import BaseCheck, CheckResult
from dqf.core.config import DQFConfig
from dqf.core.enums import DQFMode


class CustomPatternCheck(BaseCheck):
    """
    Custom check for detecting potential pump-and-dump price patterns.
    """

    def __init__(self) -> None:
        super().__init__(check_id="check_8_pattern", check_name="Pattern Detection")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CheckResult:
        try:
            self._validate_dataframe(data)

            if "close" not in data.columns:
                return self._create_fail_result(
                    message="Missing 'close' column for pattern detection",
                    severity="ERROR",
                )

            pump_threshold: float = kwargs.get("pump_threshold", 0.5)
            dump_threshold: float = kwargs.get("dump_threshold", -0.3)
            window_days: int = kwargs.get("window_days", 5)

            details: dict[str, Any] = {
                "row_count": len(data),
                "pump_threshold": pump_threshold,
                "dump_threshold": dump_threshold,
                "window_days": window_days,
            }

            returns = data["close"].pct_change(window_days)
            pump_count = int((returns > pump_threshold).sum())
            dump_count = int((returns < dump_threshold).sum())

            pump_dump_count = 0
            for i in range(len(data) - window_days * 2):
                window_returns = returns.iloc[i : i + window_days * 2]
                if (window_returns > pump_threshold).any() and (
                    window_returns < dump_threshold
                ).any():
                    pump_dump_count += 1

            details["pump_patterns"] = pump_count
            details["dump_patterns"] = dump_count
            details["pump_dump_patterns"] = pump_dump_count

            if pump_dump_count > 0:
                return self._create_warning_result(
                    message=f"Detected {pump_dump_count} potential pump-and-dump patterns",
                    details=details,
                )
            if pump_count > 5 or dump_count > 5:
                return self._create_warning_result(
                    message=f"High volatility: {pump_count} pumps, {dump_count} dumps",
                    details=details,
                )
            return self._create_pass_result(
                message="No suspicious patterns detected",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Pattern detection failed: {e}",
                exception=e,
            )


class CustomVolumeCheck(BaseCheck):
    """
    Custom check for volume anomaly detection.
    """

    def __init__(self) -> None:
        super().__init__(check_id="check_9_volume", check_name="Volume Anomaly Detection")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CheckResult:
        try:
            self._validate_dataframe(data)

            if "volume" not in data.columns:
                return self._create_fail_result(
                    message="Missing 'volume' column",
                    severity="ERROR",
                )

            spike_threshold: float = kwargs.get("spike_threshold", 10.0)
            details: dict[str, Any] = {
                "row_count": len(data),
                "spike_threshold": spike_threshold,
            }

            median_volume = data["volume"].median()
            if median_volume == 0:
                return self._create_warning_result(
                    message="Median volume is zero — cannot detect spikes",
                    details=details,
                )

            volume_ratio = data["volume"] / median_volume
            spike_count = int((volume_ratio > spike_threshold).sum())

            details["median_volume"] = float(median_volume)
            details["max_volume_ratio"] = float(volume_ratio.max())
            details["spike_count"] = spike_count

            if spike_count > 0:
                spike_dates = data.index[volume_ratio > spike_threshold].tolist()[:5]
                details["spike_dates"] = [str(d) for d in spike_dates]
                return self._create_warning_result(
                    message=f"Detected {spike_count} volume spikes (>{spike_threshold}x median)",
                    details=details,
                )
            return self._create_pass_result(
                message="No unusual volume spikes detected",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Volume anomaly detection failed: {e}",
                exception=e,
            )


def create_sample_data() -> pd.DataFrame:
    """Create sample OHLCV data with an embedded pump-and-dump pattern."""
    dates = pd.bdate_range("2024-01-02", periods=100, tz="UTC")

    close_prices = [100.0 + i * 0.5 for i in range(100)]
    # Pump days 50–54, dump days 55–59
    for i in range(50, 55):
        close_prices[i] *= 1.6
    for i in range(55, 60):
        close_prices[i] *= 0.7

    volumes = [1_000_000] * 100
    volumes[50] = 15_000_000
    volumes[55] = 12_000_000

    return pd.DataFrame(
        {
            "open": [p * 0.99 for p in close_prices],
            "high": [p * 1.02 for p in close_prices],
            "low": [p * 0.98 for p in close_prices],
            "close": close_prices,
            "volume": volumes,
        },
        index=dates,
    )


def main() -> None:
    print("\n" + "=" * 70)
    print("DQF Custom Check Examples")
    print("=" * 70)

    print("\nCreating sample data with patterns...")
    data = create_sample_data()
    print(f"  Created {len(data)} rows (business days from 2024-01-02)")
    print("  Includes pump-and-dump pattern (days 50-60)")
    print("  Includes volume spikes (days 50, 55)")

    # ------------------------------------------------------------------
    # Example 1: Single custom check
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Example 1: Single Custom Check")
    print("=" * 70)

    config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
    validator = DQFValidator(config)
    validator.add_custom_check("C8_pattern", CustomPatternCheck())
    print("  Custom check C8_pattern registered")

    report = validator.validate(data)
    print(f"\n  Overall Status : {report.overall_status}")
    print(f"  Purity Index   : {report.purity_index:.1f}/100")

    # Custom checks appear in advisory_results
    advisory = report.advisory_results
    if "C8_pattern" in advisory:
        print(f"\n  C8_pattern result : {advisory['C8_pattern']}")
    print("  Core results   :", report.core_results)
    print("  Advisory results:", advisory)

    # ------------------------------------------------------------------
    # Example 2: Multiple custom checks
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Example 2: Multiple Custom Checks")
    print("=" * 70)

    validator2 = DQFValidator(DQFConfig(mode=DQFMode.DIAGNOSTIC))
    validator2.add_custom_check("C8_pattern", CustomPatternCheck())
    validator2.add_custom_check("C9_volume", CustomVolumeCheck())
    print("  Registered: C8_pattern, C9_volume")

    report2 = validator2.validate(data)
    print(f"\n  Overall Status : {report2.overall_status}")
    print(f"  Purity Index   : {report2.purity_index:.1f}/100")

    print("\n  Advisory results:")
    for check_id, status in report2.advisory_results.items():
        icon = "" if status in ("PASS", "SKIP") else ""
        print(f"    {icon} {check_id}: {status}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    print("\nExporting report...")
    os.makedirs("_work/examples/reports", exist_ok=True)
    with open("_work/examples/reports/custom_check_report.json", "w") as fh:
        fh.write(report2.to_json())
    with open("_work/examples/reports/custom_check_report.yaml", "w") as fh:
        fh.write(report2.to_yaml())
    print("  Reports saved to _work/examples/reports/")

    print("\n" + "=" * 70)
    print("Custom check examples completed!")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  - Custom checks inherit from BaseCheck")
    print("  - Implement run(**kwargs: Any) -> CheckResult")
    print("  - Register with validator.add_custom_check(check_id, check)")
    print("  - Custom checks run as ADVISORY (WARN → WARNING, never VOID)")
    print("  - Results appear in report.advisory_results")


if __name__ == "__main__":
    main()
