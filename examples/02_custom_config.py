#!/usr/bin/env python3
"""
Example 02: Custom Configuration — DQF v1.1

Demonstrates various ways to configure DQF v1.1 validation.
"""

import sys

import pandas as pd

from dqf import DQFConfig, DQFMode, DQFValidator


def create_sample_data(weekdays_only: bool = True) -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    if weekdays_only:
        dates = pd.bdate_range("2024-01-02", periods=60, freq="B", tz="UTC")
    else:
        dates = pd.date_range("2024-01-01", periods=60, freq="D", tz="UTC")

    n = len(dates)
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.5 for i in range(n)],
            "high": [105.0 + i * 0.5 for i in range(n)],
            "low": [95.0 + i * 0.5 for i in range(n)],
            "close": [102.0 + i * 0.5 for i in range(n)],
            "volume": [1_000_000 + i * 10_000 for i in range(n)],
        },
        index=dates,
    )


def example_1_certification_mode():
    """Example 1: CERTIFICATION mode — strict, calendar required."""
    print("\n" + "=" * 70)
    print("Example 1: CERTIFICATION Mode (strict)")
    print("=" * 70)

    config = DQFConfig(mode=DQFMode.CERTIFICATION)
    data = create_sample_data(weekdays_only=True)

    validator = DQFValidator(config)
    report = validator.validate(data, calendar="NYSE")

    print(f"\n  Status   : {report.overall_status}")
    print(f"  MPI      : {report.purity_index:.1f}/100")
    print(f"  Gate     : {report.precondition_gate}")
    print(f"  Certified: {report.is_certified}")
    print(f"  UID      : {report.mif_uid[:48]}...")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 2...")


def example_2_diagnostic_mode():
    """Example 2: DIAGNOSTIC mode — lenient, calendar optional."""
    print("\n" + "=" * 70)
    print("Example 2: DIAGNOSTIC Mode (lenient)")
    print("=" * 70)

    config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
    data = create_sample_data(weekdays_only=True)

    validator = DQFValidator(config)
    # No calendar needed in DIAGNOSTIC mode
    report = validator.validate(data)

    print(f"\n  Status   : {report.overall_status}")
    print(f"  Mode     : {report.mode}")
    print(f"  Calendar : {report.calendar}")
    print(f"  MPI      : {report.purity_index:.1f}/100")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 3...")


def example_3_custom_ffill_thresholds():
    """Example 3: Tune forward-fill detection thresholds."""
    print("\n" + "=" * 70)
    print("Example 3: Custom Forward-Fill Thresholds")
    print("=" * 70)

    # Strict: warn after 1 consecutive repeat, fail after 2
    strict_config = DQFConfig(
        mode=DQFMode.CERTIFICATION,
        c4_warn_threshold=1,
        c4_max_consecutive_ffill=2,
    )

    # Lenient: warn after 5 consecutive repeats, fail after 10
    lenient_config = DQFConfig(
        mode=DQFMode.CERTIFICATION,
        c4_warn_threshold=5,
        c4_max_consecutive_ffill=10,
    )

    data = create_sample_data(weekdays_only=True)

    print("\n  Strict config:")
    v_strict = DQFValidator(strict_config)
    r_strict = v_strict.validate(data, calendar="NYSE")
    print(f"    C4 result : {r_strict.advisory_results.get('C4', 'N/A')}")
    print(f"    Status    : {r_strict.overall_status}")

    print("\n  Lenient config:")
    v_lenient = DQFValidator(lenient_config)
    r_lenient = v_lenient.validate(data, calendar="NYSE")
    print(f"    C4 result : {r_lenient.advisory_results.get('C4', 'N/A')}")
    print(f"    Status    : {r_lenient.overall_status}")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 4...")


def example_4_from_yaml():
    """Example 4: Load configuration from YAML file."""
    print("\n" + "=" * 70)
    print("Example 4: Load Config from YAML")
    print("=" * 70)

    from pathlib import Path

    import yaml

    config_dict = {
        "mode": "CERTIFICATION",
        "c4_max_consecutive_ffill": 3,
        "c4_warn_threshold": 2,
    }

    config_path = Path("_work/examples/config/dqf_v11_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False)

    print(f"\n  Created config file: {config_path}")

    config = DQFConfig.from_yaml(str(config_path))
    print(f"  Loaded: mode={config.mode.value}, c4_threshold={config.c4_warn_threshold}")

    data = create_sample_data(weekdays_only=True)
    validator = DQFValidator(config)
    report = validator.validate(data, calendar="NYSE")

    print(f"\n  Status : {report.overall_status}")
    print(f"  MPI    : {report.purity_index:.1f}/100")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 5...")


def example_5_print_summary():
    """Example 5: Human-readable summary and serialisation."""
    print("\n" + "=" * 70)
    print("Example 5: Summary and Serialisation")
    print("=" * 70)

    config = DQFConfig(mode=DQFMode.CERTIFICATION)
    data = create_sample_data(weekdays_only=True)

    validator = DQFValidator(config)
    report = validator.validate(data, calendar="NYSE")

    print()
    report.print_summary()

    # Serialise
    json_str = report.to_json()
    yaml_str = report.to_yaml()
    print(f"\n  JSON length : {len(json_str)} chars")
    print(f"  YAML length : {len(yaml_str)} chars")


def main():
    """Run all examples."""
    print("\n")
    print("DQF v1.1 Custom Configuration Examples")
    print("=" * 70)

    example_1_certification_mode()
    example_2_diagnostic_mode()
    example_3_custom_ffill_thresholds()
    example_4_from_yaml()
    example_5_print_summary()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
