#!/usr/bin/env python3
"""
Example 04: Custom Check Implementation

Demonstrates how to create and use custom validation checks.
"""

from typing import Any

import pandas as pd

from dqf import DQFValidator
from dqf.checks.base import BaseCheck, CheckResult


class CustomPatternCheck(BaseCheck):
    """
    Custom check for detecting specific price patterns.

    Example: Detect potential pump-and-dump patterns.
    """

    def __init__(self):
        """Initialize custom pattern check."""
        super().__init__(check_id="check_8_pattern", check_name="Pattern Detection")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Run pattern detection check.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - pump_threshold: float (default: 0.5, i.e., 50% increase)
                - dump_threshold: float (default: -0.3, i.e., 30% decrease)
                - window_days: int (default: 5)

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)

            if "close" not in data.columns:
                return self._create_fail_result(
                    message="Missing 'close' column for pattern detection",
                    severity="ERROR",
                )

            # Extract parameters
            pump_threshold = kwargs.get("pump_threshold", 0.5)
            dump_threshold = kwargs.get("dump_threshold", -0.3)
            window_days = kwargs.get("window_days", 5)

            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "pump_threshold": pump_threshold,
                "dump_threshold": dump_threshold,
                "window_days": window_days,
            }

            # Calculate returns over window
            returns = data["close"].pct_change(window_days)

            # Detect pump patterns (sharp increase)
            pumps = returns > pump_threshold
            pump_count = pumps.sum()

            # Detect dump patterns (sharp decrease)
            dumps = returns < dump_threshold
            dump_count = dumps.sum()

            # Detect pump-and-dump (pump followed by dump within window)
            pump_dump_count = 0
            for i in range(len(data) - window_days * 2):
                window_returns = returns.iloc[i : i + window_days * 2]
                if (window_returns > pump_threshold).any() and (
                    window_returns < dump_threshold
                ).any():
                    pump_dump_count += 1

            details["pump_patterns"] = int(pump_count)
            details["dump_patterns"] = int(dump_count)
            details["pump_dump_patterns"] = pump_dump_count

            # Determine result
            if pump_dump_count > 0:
                return self._create_warning_result(
                    message=f"Detected {pump_dump_count} potential pump-and-dump patterns",
                    details=details,
                )

            if pump_count > 5 or dump_count > 5:
                return self._create_warning_result(
                    message=f"High volatility detected: {pump_count} pumps, {dump_count} dumps",
                    details=details,
                )

            return self._create_pass_result(
                message="No suspicious patterns detected",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Pattern detection failed: {str(e)}",
                exception=e,
            )


class CustomVolumeCheck(BaseCheck):
    """
    Custom check for volume anomalies.

    Example: Detect unusual volume spikes that might indicate manipulation.
    """

    def __init__(self):
        """Initialize custom volume check."""
        super().__init__(check_id="check_9_volume", check_name="Volume Anomaly Detection")

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Run volume anomaly detection.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - spike_threshold: float (default: 10.0, i.e., 10x median)

        Returns:
            CheckResult with validation outcome
        """
        try:
            self._validate_dataframe(data)

            if "volume" not in data.columns:
                return self._create_fail_result(
                    message="Missing 'volume' column for anomaly detection",
                    severity="ERROR",
                )

            spike_threshold = kwargs.get("spike_threshold", 10.0)

            details = {
                "symbol": symbol,
                "source": source,
                "row_count": len(data),
                "spike_threshold": spike_threshold,
            }

            # Calculate volume statistics
            median_volume = data["volume"].median()

            if median_volume == 0:
                return self._create_warning_result(
                    message="Median volume is zero - cannot detect spikes",
                    details=details,
                )

            # Detect spikes
            volume_ratio = data["volume"] / median_volume
            spikes = volume_ratio > spike_threshold
            spike_count = spikes.sum()

            details["median_volume"] = float(median_volume)
            details["max_volume_ratio"] = float(volume_ratio.max())
            details["spike_count"] = int(spike_count)

            if spike_count > 0:
                spike_dates = data.index[spikes].tolist()[:5]  # First 5 spikes
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
                message=f"Volume anomaly detection failed: {str(e)}",
                exception=e,
            )


def create_sample_data():
    """Create sample data with some patterns for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")

    # Create base data
    close_prices = [100.0 + i * 0.5 for i in range(100)]

    # Add a pump-and-dump pattern around day 50
    for i in range(50, 55):
        close_prices[i] *= 1.6  # 60% pump
    for i in range(55, 60):
        close_prices[i] *= 0.7  # 30% dump

    # Create volumes with some spikes
    volumes = [1000000] * 100
    volumes[50] = 15000000  # 15x spike during pump
    volumes[55] = 12000000  # 12x spike during dump

    data = pd.DataFrame(
        {
            "open": [p * 0.99 for p in close_prices],
            "high": [p * 1.02 for p in close_prices],
            "low": [p * 0.98 for p in close_prices],
            "close": close_prices,
            "volume": volumes,
        },
        index=dates,
    )

    return data


def main():
    """Run custom check examples."""
    print("\n" + "=" * 70)
    print("🔧 DQF Custom Check Examples")
    print("=" * 70)

    # Create sample data
    print("\n📊 Creating sample data with patterns...")
    data = create_sample_data()
    print(f"✅ Created {len(data)} rows of data")
    print("   - Includes pump-and-dump pattern (days 50-60)")
    print("   - Includes volume spikes (days 50, 55)")

    # Example 1: Single custom check
    print("\n" + "=" * 70)
    print("Example 1: Single Custom Check")
    print("=" * 70)

    print("\n⚙️  Creating validator with pattern detection check...")
    validator = DQFValidator()

    # Add custom check
    pattern_check = CustomPatternCheck()
    validator.add_custom_check("check_8_pattern", pattern_check)

    print("✅ Custom check added")

    # Run validation
    print("\n🔍 Running validation...")
    report = validator.validate(data, symbol="TEST-USD", source="custom")

    # Show results
    print("\n📋 Results:")
    print(f"   Overall Status: {report.overall_status}")
    print(f"   Total Checks: {report.total_checks} (7 standard + 1 custom)")
    print(f"   Checks Passed: {report.checks_passed}/{report.total_checks}")

    # Show custom check result
    if "Pattern Detection" in report.check_results:
        result = report.check_results["Pattern Detection"]
        print("\n   📌 Pattern Detection Result:")
        print(f"      Status: {result.status}")
        print(f"      Message: {result.message}")
        if result.details:
            print(f"      Pump patterns: {result.details.get('pump_patterns', 0)}")
            print(f"      Dump patterns: {result.details.get('dump_patterns', 0)}")
            print(f"      Pump-dump patterns: {result.details.get('pump_dump_patterns', 0)}")

    # Example 2: Multiple custom checks
    print("\n" + "=" * 70)
    print("Example 2: Multiple Custom Checks")
    print("=" * 70)

    print("\n⚙️  Creating validator with multiple custom checks...")
    validator2 = DQFValidator()

    # Add both custom checks
    validator2.add_custom_check("check_8_pattern", CustomPatternCheck())
    validator2.add_custom_check("check_9_volume", CustomVolumeCheck())

    print("✅ 2 custom checks added")

    # Run validation
    print("\n🔍 Running validation...")
    report2 = validator2.validate(
        data,
        symbol="TEST-USD",
        source="custom",
        pump_threshold=0.4,  # Custom parameter for pattern check
        spike_threshold=8.0,  # Custom parameter for volume check
    )

    # Show results
    print("\n📋 Results:")
    print(f"   Overall Status: {report2.overall_status}")
    print(f"   Total Checks: {report2.total_checks} (7 standard + 2 custom)")
    print(f"   Checks Passed: {report2.checks_passed}/{report2.total_checks}")

    # Show all check results
    print("\n   📌 All Check Results:")
    for check_name, result in report2.check_results.items():
        status_icon = (
            "✅" if result.status == "PASS" else "⚠️" if result.status == "WARNING" else "❌"
        )
        print(f"      {status_icon} {check_name}: {result.status}")

    # Export report
    print("\n💾 Exporting report...")
    report2.to_yaml("_work/examples/reports/custom_check_report.yaml")
    report2.to_json("_work/examples/reports/custom_check_report.json")
    print("   ✅ Reports saved to _work/examples/reports/")

    print("\n" + "=" * 70)
    print("✅ Custom check examples completed!")
    print("=" * 70)
    print("\n💡 Key takeaways:")
    print("   - Custom checks inherit from BaseCheck")
    print("   - Must implement run() method with **kwargs")
    print("   - Use helper methods (_create_pass_result, etc.)")
    print("   - Can accept custom parameters via kwargs")
    print("   - Add to validator with add_custom_check()")
    print()


if __name__ == "__main__":
    main()
