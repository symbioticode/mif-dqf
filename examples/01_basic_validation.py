#!/usr/bin/env python3
"""
DQF Example 01: Basic Validation

Demonstrates:
- Loading OHLCV data
- Running validation with default config
- Interpreting results
- Exporting report

Usage:
    python examples/01_basic_validation.py
"""

from pathlib import Path

import pandas as pd

from dqf import DQFConfig, DQFValidator


def main():
    print("=" * 60)
    print("DQF Example 01: Basic Validation")
    print("=" * 60)
    print()

    # Step 1: Load sample data
    print("📊 Step 1: Loading sample data...")

    # Create sample BTC-USD data (187 days)
    dates = pd.date_range("2024-01-01", periods=188, freq="D", tz="UTC")
    data = pd.DataFrame(
        {
            "open": [45000 + i * 10 for i in range(len(dates))],
            "high": [45500 + i * 10 for i in range(len(dates))],
            "low": [44500 + i * 10 for i in range(len(dates))],
            "close": [45200 + i * 10 for i in range(len(dates))],
            "volume": [1000000 + i * 1000 for i in range(len(dates))],
        },
        index=dates,
    )

    print(f"✅ Loaded {len(data)} rows of BTC-USD data")
    print(f"   Date range: {data.index[0]} to {data.index[-1]}")
    print()

    # Display sample
    print("📈 Sample data (first 5 rows):")
    print(data.head())
    print()

    # Step 2: Create default configuration
    print("⚙️  Step 2: Creating default configuration...")
    config = DQFConfig()
    print("✅ Default config created")
    print("   - All 7 checks enabled")
    print("   - Standard thresholds")
    print()

    # Step 3: Run validation
    print("🔍 Step 3: Running validation...")
    validator = DQFValidator(config)
    report = validator.validate(data)
    print("✅ Validation complete")
    print()

    # Step 4: Interpret results
    print("=" * 60)
    print("📋 VALIDATION RESULTS")
    print("=" * 60)
    print()

    print(f"Overall Status: {report.overall_status}")
    print(f"Checks Passed:  {report.checks_passed}/{report.total_checks}")
    print(f"Issues Found:   {len(report.all_issues)}")
    print()

    # Individual check results
    print("Individual Check Results:")
    print("-" * 60)
    for check_name, result in report.check_results.items():
        status_icon = "✅" if result.status == "PASS" else "❌"
        print(f"{status_icon} {check_name}: {result.status}")
        if result.message:
            print(f"   Message: {result.message}")
    print()

    # Issues (if any)
    if report.all_issues:
        print("⚠️  Issues Detected:")
        print("-" * 60)
        for issue in report.all_issues:
            print(f"[{issue.severity}] {issue.check_name}")
            print(f"   {issue.message}")
        print()
    else:
        print("✅ No issues detected - data is clean!")
        print()

    # Step 5: Access cleaned data
    if report.overall_status == "PASS":
        print("✅ Step 5: Accessing cleaned data...")
        clean_data = report.cleaned_data
        print(f"   Shape: {clean_data.shape}")
        print(f"   Columns: {list(clean_data.columns)}")
        print()

        # Save cleaned data (optional)
        output_dir = Path("_work/examples")
        output_dir.mkdir(parents=True, exist_ok=True)

        clean_data.to_csv(output_dir / "btc_usd_clean.csv")
        print(f"   💾 Saved: {output_dir / 'btc_usd_clean.csv'}")
        print()
    else:
        print("❌ Validation failed - data not clean")
        print("   Fix issues before using data in production")
        print()

    # Step 6: Export report
    print("📄 Step 6: Exporting report...")
    report_dir = Path("_work/examples/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    # Export as YAML (human-readable)
    yaml_path = report_dir / "validation_report.yaml"
    report.to_yaml(str(yaml_path))
    print(f"   💾 YAML: {yaml_path}")

    # Export as JSON (machine-readable)
    json_path = report_dir / "validation_report.json"
    report.to_json(str(json_path))
    print(f"   💾 JSON: {json_path}")
    print()

    # Step 7: Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print()
    print(f"✅ Validation {'PASSED' if report.overall_status == 'PASS' else 'FAILED'}")
    print(f"✅ {report.checks_passed} checks passed")
    print(f"✅ Reports exported to: {report_dir}")

    if report.overall_status == "PASS":
        print(f"✅ Clean data saved to: {output_dir}")

    print()
    print("💡 Next steps:")
    print("   - Review report files for details")
    print("   - Try examples/02_custom_config.py for advanced config")
    print("   - Use cleaned data in your analysis/trading pipeline")
    print()


if __name__ == "__main__":
    main()
