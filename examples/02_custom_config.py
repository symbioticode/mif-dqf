#!/usr/bin/env python3
"""
Example 02: Custom Configuration

Demonstrates various ways to configure DQF validation checks.
"""

import sys
from pathlib import Path

import pandas as pd

from dqf import DQFConfig, DQFValidator


def create_sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")

    data = pd.DataFrame(
        {
            "open": [100.0 + i * 0.5 for i in range(100)],
            "high": [105.0 + i * 0.5 for i in range(100)],
            "low": [95.0 + i * 0.5 for i in range(100)],
            "close": [102.0 + i * 0.5 for i in range(100)],
            "volume": [1000000 + i * 10000 for i in range(100)],
        },
        index=dates,
    )

    return data


def example_1_yaml_config():
    """Example 1: Load configuration from YAML file."""
    print("\n" + "=" * 70)
    print("Example 1: Custom YAML Configuration")
    print("=" * 70)

    # Create custom config
    config_dict = {
        "checks": {
            "check_1_source": {
                "enabled": True,
                "require_metadata": True,
                "max_gap_days": 7,
            },
            "check_2_integrity": {
                "enabled": True,
                "max_violation_rate": 0.005,
            },
            "check_3_calendar": {
                "enabled": True,
                "auto_detect": True,
                "require_timezone": True,
            },
            "check_4_ffill": {
                "enabled": True,
                "max_consecutive_ffill": 2,
                "warn_threshold": 1,
            },
            "check_5_trace": {
                "enabled": True,
                "require_unique": True,
                "require_chronological": True,
            },
            "check_6_sanity": {
                "enabled": False,  # Disabled for performance
            },
            "check_7_logging": {
                "enabled": False,  # Disabled for this example
            },
        }
    }

    # Save to YAML
    config_path = Path("_work/examples/config/custom_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    import yaml

    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False)

    print(f"\n✅ Created config file: {config_path}")

    # Load from YAML
    print("\n📄 Loading config from YAML...")
    config = DQFConfig.from_yaml(str(config_path))
    print("✅ Config loaded successfully")

    # Run validation
    data = create_sample_data()
    validator = DQFValidator(config)
    report = validator.validate(data, symbol="BTC-USD", source="test")

    # Show results
    print("\n📋 Results with custom config:")
    print(f"   Overall Status: {report.overall_status}")
    print(f"   Checks Passed: {report.checks_passed}/{report.total_checks}")

    for check_name, result in report.check_results.items():
        status_icon = "✅" if result.status == "PASS" else "❌"
        print(f"   {status_icon} {check_name}: {result.message}")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 2...")


def example_2_programmatic_config():
    """Example 2: Create configuration programmatically."""
    print("\n" + "=" * 70)
    print("Example 2: Programmatic Configuration")
    print("=" * 70)

    print("\n⚙️  Creating config with custom parameters...")

    # Create config with kwargs
    config = DQFConfig(
        check_2_integrity={
            "enabled": True,
            "max_violation_rate": 0.05,  # More lenient
        },
        check_4_ffill={
            "enabled": True,
            "max_consecutive_ffill": 5,  # Allow longer sequences
            "warn_threshold": 3,
        },
        check_6_sanity={
            "enabled": True,
            "extreme_return_threshold": 2.0,  # 200% daily return threshold
        },
    )

    print("✅ Config created")

    # Run validation
    data = create_sample_data()
    validator = DQFValidator(config)
    report = validator.validate(data, symbol="BTC-USD", source="test")

    # Show results
    print("\n📋 Results with loose config:")
    print(f"   Overall Status: {report.overall_status}")
    print(f"   Checks Passed: {report.checks_passed}/{report.total_checks}")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 3...")


def example_3_selective_checks():
    """Example 3: Run only specific checks."""
    print("\n" + "=" * 70)
    print("Example 3: Selective Check Execution")
    print("=" * 70)

    print("\n⚙️  Disabling slow checks (sanity tests, logging)...")

    # Disable specific checks
    config = DQFConfig(
        check_6_sanity={"enabled": False},
        check_7_logging={"enabled": False},
    )

    print("✅ Config created (only 5/7 checks enabled)")

    # Run validation
    data = create_sample_data()
    validator = DQFValidator(config)
    report = validator.validate(data, symbol="BTC-USD", source="test")

    # Show results
    print("\n📋 Results with selective checks:")
    print(f"   Overall Status: {report.overall_status}")
    print(f"   Checks Run: {report.total_checks}")

    print("\n   Checks executed:")
    for check_name, result in report.check_results.items():
        status_icon = "✅" if result.status == "PASS" else "❌"
        print(f"   {status_icon} {check_name}")

    print("\n   💡 Useful for:")
    print("      - Quick validation (skip slow checks)")
    print("      - Debugging specific checks")
    print("      - Production pipelines (skip unnecessary checks)")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 4...")


def example_4_modify_existing_config():
    """Example 4: Modify an existing configuration."""
    print("\n" + "=" * 70)
    print("Example 4: Modify Existing Configuration")
    print("=" * 70)

    # Load existing config
    config_path = "_work/examples/config/custom_config.yaml"
    print(f"\n📄 Loading existing config: {config_path}")
    config = DQFConfig.from_yaml(config_path)
    print("✅ Config loaded")

    # Modify config
    print("\n🔧 Modifying config...")
    print("   - Enabling check_6_sanity (was disabled)")
    print("   - Loosening forward-fill threshold (1 → 3 days)")

    # Modify using the checks dict
    config.checks["check_6_sanity"]["enabled"] = True
    config.checks["check_4_ffill"]["max_consecutive_ffill"] = 3

    print("✅ Config modified")

    # Run validation
    data = create_sample_data()
    validator = DQFValidator(config)
    report = validator.validate(data, symbol="BTC-USD", source="test")

    # Show results
    print("\n📋 Results with modified config:")
    print(f"   Overall Status: {report.overall_status}")
    print(f"   Checks Passed: {report.checks_passed}/{report.total_checks}")

    # Save modified config
    new_config_path = Path("_work/examples/config/modified_config.yaml")
    config.to_yaml(str(new_config_path))
    print(f"\n💾 Modified config saved to: {new_config_path}")

    if sys.stdin.isatty():
        input("\nPress Enter to continue to Example 5...")


def example_5_config_inheritance():
    """Example 5: Config inheritance and override patterns."""
    print("\n" + "=" * 70)
    print("Example 5: Configuration Inheritance")
    print("=" * 70)

    print("\n⚙️  Creating base config...")

    # Base config (strict)
    base_config = DQFConfig(
        check_2_integrity={"max_violation_rate": 0.001},  # Very strict
        check_4_ffill={"max_consecutive_ffill": 1},  # Very strict
    )

    print("✅ Base config created (strict)")

    # Development config (lenient, based on base)
    print("\n⚙️  Creating dev config (override base)...")

    dev_config = DQFConfig(
        check_2_integrity={"max_violation_rate": 0.05},  # Lenient
        check_4_ffill={"max_consecutive_ffill": 5},  # Lenient
        check_6_sanity={"enabled": False},  # Skip slow checks
        check_7_logging={"enabled": False},
    )

    print("✅ Dev config created (lenient)")

    # Compare results
    data = create_sample_data()

    print("\n📊 Comparing configs:")

    # Strict validation
    validator_strict = DQFValidator(base_config)
    report_strict = validator_strict.validate(data, symbol="BTC-USD", source="test")
    print("\n   Strict config:")
    print(f"      Status: {report_strict.overall_status}")
    print(f"      Passed: {report_strict.checks_passed}/{report_strict.total_checks}")

    # Lenient validation
    validator_lenient = DQFValidator(dev_config)
    report_lenient = validator_lenient.validate(data, symbol="BTC-USD", source="test")
    print("\n   Lenient config:")
    print(f"      Status: {report_lenient.overall_status}")
    print(f"      Passed: {report_lenient.checks_passed}/{report_lenient.total_checks}")

    print("\n   💡 Use case:")
    print("      - Strict for production data")
    print("      - Lenient for development/testing")


def main():
    """Run all examples."""
    print("\n")
    print("🔧 DQF Custom Configuration Examples")
    print("=" * 70)

    example_1_yaml_config()
    example_2_programmatic_config()
    example_3_selective_checks()
    example_4_modify_existing_config()
    example_5_config_inheritance()

    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   - Customize configs for your specific needs")
    print("   - Export configs to YAML for reuse")
    print("   - Use different configs for dev vs production")
    print()


if __name__ == "__main__":
    main()
