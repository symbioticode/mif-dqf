#!/usr/bin/env python3
"""
DQF Example 03: Batch Processing

Demonstrates:
- Validating multiple symbols/files
- Aggregating results
- Filtering PASS/FAIL datasets
- Generating summary report
- Parallel processing (optional)

Usage:
    python examples/03_batch_processing.py
"""

from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from dqf import DQFConfig, DQFValidator


def create_sample_datasets() -> Dict[str, pd.DataFrame]:
    """Create sample datasets for multiple symbols"""
    symbols = ["BTC-USD", "ETH-USD", "SPY", "GLD", "EUR-USD"]
    datasets = {}

    base_date = pd.date_range(start="2024-01-01", end="2024-07-06", freq="D")

    for symbol in symbols:
        # Vary base price per symbol
        base_prices = {
            "BTC-USD": 45000,
            "ETH-USD": 2500,
            "SPY": 450,
            "GLD": 180,
            "EUR-USD": 1.08,
        }

        base_price = base_prices[symbol]

        data = pd.DataFrame(
            {
                "open": [base_price + i * 0.1 for i in range(len(base_date))],
                "high": [base_price * 1.01 + i * 0.1 for i in range(len(base_date))],
                "low": [base_price * 0.99 + i * 0.1 for i in range(len(base_date))],
                "close": [base_price + i * 0.1 for i in range(len(base_date))],
                "volume": [1000000 + i * 1000 for i in range(len(base_date))],
            },
            index=base_date,
        )

        # Introduce issues in some datasets (for demonstration)
        if symbol == "EUR-USD":
            # Add forward-fill issue
            data.loc[data.index[10:15], "close"] = data.loc[data.index[9], "close"]

        if symbol == "GLD":
            # Add OHLCV violation (High < Low)
            data.loc[data.index[50], "high"] = data.loc[data.index[50], "low"] - 1

        datasets[symbol] = data

    return datasets


def batch_validate_sequential(
    datasets: Dict[str, pd.DataFrame], config: DQFConfig
) -> Dict[str, object]:
    """Validate datasets sequentially"""
    print("🔄 Sequential Validation")
    print("-" * 70)

    validator = DQFValidator(config)
    results = {}

    for symbol, data in datasets.items():
        print(f"   Validating {symbol}... ", end="", flush=True)

        try:
            report = validator.validate(data)
            results[symbol] = report

            status_icon = "✅" if report.overall_status == "PASS" else "❌"
            print(f"{status_icon} {report.overall_status}")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results[symbol] = None

    print()
    return results


def generate_summary_report(results: Dict[str, object]) -> None:
    """Generate summary report across all validations"""
    print("=" * 70)
    print("📊 BATCH VALIDATION SUMMARY")
    print("=" * 70)
    print()

    # Count PASS/FAIL
    passed = sum(1 for r in results.values() if r and r.overall_status == "PASS")
    failed = sum(1 for r in results.values() if r and r.overall_status == "FAIL")
    errors = sum(1 for r in results.values() if r is None)

    print(f"Total Datasets:  {len(results)}")
    print(f"✅ Passed:        {passed}")
    print(f"❌ Failed:        {failed}")
    print(f"⚠️  Errors:        {errors}")
    print()

    # Detailed results per symbol
    print("Detailed Results:")
    print("-" * 70)

    for symbol, report in results.items():
        if report is None:
            print(f"❌ {symbol:12s} - ERROR (validation crashed)")
            continue

        status_icon = "✅" if report.overall_status == "PASS" else "❌"
        checks_str = f"{report.checks_passed}/{report.total_checks}"
        issues_str = f"{len(report.all_issues)} issues"

        print(
            f"{status_icon} {symbol:12s} - {report.overall_status:4s} | "
            f"Checks: {checks_str} | {issues_str}"
        )

        # Show first issue (if any)
        if report.all_issues:
            first_issue = report.all_issues[0]
            print(f"   └─ [{first_issue.severity}] {first_issue.message[:60]}")

    print()


def filter_clean_datasets(
    datasets: Dict[str, pd.DataFrame], results: Dict[str, object]
) -> Dict[str, pd.DataFrame]:
    """Filter only datasets that passed validation"""
    print("🔍 Filtering Clean Datasets")
    print("-" * 70)

    clean = {}

    for symbol, report in results.items():
        if report and report.overall_status == "PASS":
            clean[symbol] = report.cleaned_data
            print(f"   ✅ {symbol:12s} - {len(report.cleaned_data)} rows")

    print()
    print(f"✅ {len(clean)}/{len(datasets)} datasets passed validation")
    print()

    return clean


def export_results(results: Dict[str, object], output_dir: Path) -> None:
    """Export all reports to files"""
    print("💾 Exporting Results")
    print("-" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)

    for symbol, report in results.items():
        if report is None:
            continue

        # Create symbol-specific directory
        symbol_dir = output_dir / symbol.replace("/", "_")
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Export report
        yaml_path = symbol_dir / "validation_report.yaml"
        report.to_yaml(str(yaml_path))

        # Export cleaned data (if PASS)
        if report.overall_status == "PASS":
            csv_path = symbol_dir / f"{symbol.replace('/', '_')}_clean.csv"
            report.cleaned_data.to_csv(csv_path)
            print(f"   ✅ {symbol:12s} - Report + Clean data")
        else:
            print(f"   ❌ {symbol:12s} - Report only (failed validation)")

    print()
    print(f"📁 All results saved to: {output_dir}")
    print()


def create_consolidated_report(results: Dict[str, object], output_path: Path) -> None:
    """Create single consolidated CSV report"""
    print("📄 Creating Consolidated Report")
    print("-" * 70)

    rows = []

    for symbol, report in results.items():
        if report is None:
            rows.append(
                {
                    "symbol": symbol,
                    "status": "ERROR",
                    "checks_passed": 0,
                    "total_checks": 0,
                    "issues_count": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            continue

        rows.append(
            {
                "symbol": symbol,
                "status": report.overall_status,
                "checks_passed": report.checks_passed,
                "total_checks": report.total_checks,
                "issues_count": len(report.all_issues),
                "timestamp": report.timestamp,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)

    print(f"   ✅ Consolidated report: {output_path}")
    print()


def example_basic_batch():
    """Example: Basic batch processing"""
    print("=" * 70)
    print("Example: Basic Batch Processing")
    print("=" * 70)
    print()

    # Create sample datasets
    print("📊 Creating sample datasets...")
    datasets = create_sample_datasets()
    print(f"✅ Created {len(datasets)} datasets")
    print(f"   Symbols: {', '.join(datasets.keys())}")
    print()

    # Configure validator
    config = DQFConfig()

    # Run batch validation
    results = batch_validate_sequential(datasets, config)

    # Generate summary
    generate_summary_report(results)

    # Filter clean datasets
    clean_datasets = filter_clean_datasets(datasets, results)
    print(f"✅ {len(clean_datasets)} datasets passed validation")

    # Export results
    output_dir = Path("_work/examples/batch_results")
    export_results(results, output_dir)

    # Create consolidated report
    consolidated_path = output_dir / "consolidated_report.csv"
    create_consolidated_report(results, consolidated_path)


def example_custom_config_batch():
    """Example: Batch with custom config (stricter validation)"""
    print("=" * 70)
    print("Example: Batch with Strict Configuration")
    print("=" * 70)
    print()

    # Strict config
    config = DQFConfig(
        check_2_integrity={
            "enabled": True,
            "max_violation_rate": 0.0,  # Zero tolerance
        },
        check_4_ffill={
            "enabled": True,
            "max_consecutive": 1,  # Very strict
            "severity": "CRITICAL",
        },
    )

    print("⚙️  Using strict configuration:")
    print("   - Zero tolerance for OHLCV violations")
    print("   - Max 1 day forward-fill")
    print()

    # Create datasets
    datasets = create_sample_datasets()

    # Validate
    results = batch_validate_sequential(datasets, config)

    # Summary
    generate_summary_report(results)

    print("💡 Notice: More datasets failed with strict config")
    print()


def main():
    print("\n")
    print("📦 DQF Batch Processing Examples")
    print("=" * 70)
    print()

    # Run examples
    example_basic_batch()

    input("Press Enter to run strict config example...")
    print()

    example_custom_config_batch()

    # Final summary
    print("=" * 70)
    print("✅ BATCH PROCESSING COMPLETE")
    print("=" * 70)
    print()
    print("💡 Key Features:")
    print("   ✅ Validate multiple symbols/files in one run")
    print("   ✅ Aggregate results with summary statistics")
    print("   ✅ Filter only clean datasets for downstream use")
    print("   ✅ Export reports per symbol + consolidated CSV")
    print()
    print("📖 Next Steps:")
    print("   - Use clean datasets in your analysis pipeline")
    print("   - Investigate failed datasets (detailed reports)")
    print("   - Adjust config thresholds based on results")
    print()
    print("🔧 Advanced: See examples/04_custom_check.py for custom checks")
    print()


if __name__ == "__main__":
    main()
