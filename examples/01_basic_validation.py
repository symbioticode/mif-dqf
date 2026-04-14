#!/usr/bin/env python3
"""
DQF Example 01: Basic Validation — v1.1

Demonstrates:
- DIAGNOSTIC mode: quick validation, no calendar required
- CERTIFICATION mode: strict validation with calendar
- Interpreting the MIF-Lite report (status, MPI, gate, UID)
- Exporting the manifest (JSON / YAML)

Usage:
    python examples/01_basic_validation.py
"""

from pathlib import Path

import pandas as pd

from dqf import DQFConfig, DQFMode, DQFValidator


def create_btc_data(periods: int = 60) -> pd.DataFrame:
    """Synthetic BTC-USD daily data (CRYPTO_247 — weekends allowed)."""
    dates = pd.date_range("2024-01-01", periods=periods, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [45_000 + i * 10 for i in range(len(dates))],
            "high": [45_500 + i * 10 for i in range(len(dates))],
            "low": [44_500 + i * 10 for i in range(len(dates))],
            "close": [45_200 + i * 10 for i in range(len(dates))],
            "volume": [1_000_000 + i * 1_000 for i in range(len(dates))],
        },
        index=dates,
    )


def create_spy_data(periods: int = 40) -> pd.DataFrame:
    """Synthetic SPY weekday-only data (NYSE calendar)."""
    dates = pd.bdate_range("2024-01-02", periods=periods, freq="B", tz="UTC")
    return pd.DataFrame(
        {
            "open": [450.0 + i * 0.5 for i in range(len(dates))],
            "high": [455.0 + i * 0.5 for i in range(len(dates))],
            "low": [445.0 + i * 0.5 for i in range(len(dates))],
            "close": [452.0 + i * 0.5 for i in range(len(dates))],
            "volume": [50_000_000] * len(dates),
        },
        index=dates,
    )


def example_diagnostic_mode():
    """DIAGNOSTIC mode — lenient, no calendar required."""
    print("=" * 60)
    print("Step 1 — DIAGNOSTIC mode (BTC-USD, no calendar)")
    print("=" * 60)

    data = create_btc_data()
    config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
    validator = DQFValidator(config)

    report = validator.validate(data)

    print(f"  Status   : {report.overall_status}")
    print(f"  MPI      : {report.purity_index:.1f}/100")
    print(f"  Gate     : {report.precondition_gate}")
    print(f"  Calendar : {report.calendar}")
    print(f"  Mode     : {report.mode}")
    print(f"  UID      : {report.mif_uid[:48]}...")
    print()

    print("  CORE checks:")
    for check_id, status in report.core_results.items():
        icon = "OK" if status in ("PASS", "SKIP") else "FAIL"
        print(f"    [{icon}] {check_id}: {status}")

    print("  ADVISORY checks:")
    for check_id, status in report.advisory_results.items():
        icon = "OK" if status in ("PASS", "SKIP") else "WARN"
        print(f"    [{icon}] {check_id}: {status}")
    print()

    return report


def example_certification_mode():
    """CERTIFICATION mode — strict, calendar required."""
    print("=" * 60)
    print("Step 2 — CERTIFICATION mode (SPY / NYSE)")
    print("=" * 60)

    data = create_spy_data()
    config = DQFConfig(mode=DQFMode.CERTIFICATION)
    validator = DQFValidator(config)

    report = validator.validate(data, calendar="NYSE")

    print(f"  Status    : {report.overall_status}")
    print(f"  Certified : {report.is_certified}")
    print(f"  MPI       : {report.purity_index:.1f}/100")
    print(f"  Gate      : {report.precondition_gate}")
    print(f"  Vitality  : {report.vitality_label}")
    print()

    if report.is_certified:
        print("  Data is certified — safe for production use.")
    else:
        print(f"  Certification failed — gate={report.precondition_gate}")
    print()

    return report


def example_export_report(report):
    """Export the MIF-Lite manifest as JSON and YAML."""
    print("=" * 60)
    print("Step 3 — Export MIF-Lite manifest")
    print("=" * 60)

    output_dir = Path("_work/examples/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # to_json() and to_yaml() return strings — write them manually
    json_path = output_dir / "validation_report.json"
    yaml_path = output_dir / "validation_report.yaml"

    json_path.write_text(report.to_json())
    yaml_path.write_text(report.to_yaml())

    print(f"  JSON : {json_path}  ({json_path.stat().st_size} bytes)")
    print(f"  YAML : {yaml_path}  ({yaml_path.stat().st_size} bytes)")
    print()

    # Human-readable summary
    report.print_summary()


def example_use_certified_data(report):
    """Access the validated DataFrame for downstream use."""
    print("=" * 60)
    print("Step 4 — Use validated data")
    print("=" * 60)

    if report.is_certified:
        clean = report.cleaned_data
        print(f"  Shape  : {clean.shape}")
        print(f"  Columns: {list(clean.columns)}")

        output_dir = Path("_work/examples")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "spy_certified.csv"
        clean.to_csv(csv_path)
        print(f"  Saved  : {csv_path}")
    else:
        print("  Certification required before using data in production.")
    print()


def main():
    print("\n")
    print("DQF v1.1 — Basic Validation Example")
    print("=" * 60)
    print()

    # 1. Quick diagnostic run
    example_diagnostic_mode()

    # 2. Strict certification run
    report = example_certification_mode()

    # 3. Export manifest
    example_export_report(report)

    # 4. Use certified data
    example_use_certified_data(report)

    print("Done. Next: python examples/02_custom_config.py")
    print()


if __name__ == "__main__":
    main()
