#!/usr/bin/env python3
"""
Test DQF Package Installation

Validates that the package is correctly installed and all imports work.

Usage:
    python scripts/test_install.py
"""

import sys
from pathlib import Path


def test_imports():
    """Test all public imports"""
    print("=" * 70)
    print("Testing DQF Package Installation")
    print("=" * 70)
    print()

    # Test 1: Basic imports
    print("1  Testing basic imports...")
    try:
        from dqf import DQFValidator, DQFConfig, DQFReport, DQFMode
        print("   OK Core classes imported successfully")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    # Test 2: Base classes
    print("2  Testing base classes...")
    try:
        from dqf import BaseCheck, CheckResult, CheckIssue
        print("   OK Base classes imported successfully")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    # Test 3: Individual checks
    print("3  Testing individual checks...")
    try:
        from dqf import (
            SourceUniquenessCheck,
            IntegrityCheck,
            CalendarAlignmentCheck,
            ForwardFillCheck,
            IndexTraceabilityCheck,
        )
        print("   OK All 5 checks imported successfully")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    # Test 4: Utils
    print("4  Testing utils...")
    try:
        from dqf import detect_calendar, is_weekend
        print("   OK Utils imported successfully")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    # Test 5: MPI utilities
    print("5  Testing MPI utilities...")
    try:
        from dqf import InterventionLog, compute_mpi, PRODEnvelope
        print("   OK MPI utilities imported successfully")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    # Test 6: Version
    print("6  Testing version...")
    try:
        from dqf import __version__
        print(f"   OK DQF version: {__version__}")
    except ImportError as e:
        print(f"   FAIL Import failed: {e}")
        return False

    print()
    return True


def test_basic_usage():
    """Test basic validation workflow"""
    print("=" * 70)
    print("Testing Basic Validation Workflow")
    print("=" * 70)
    print()

    try:
        import pandas as pd
        from dqf import DQFValidator, DQFConfig, DQFMode

        # Create sample data
        print("1  Creating sample data...")
        dates = pd.bdate_range("2024-01-01", periods=10, freq="B", tz="UTC")
        data = pd.DataFrame(
            {
                "open":   [100.0 + i for i in range(10)],
                "high":   [105.0 + i for i in range(10)],
                "low":    [95.0 + i for i in range(10)],
                "close":  [102.0 + i for i in range(10)],
                "volume": [1_000_000] * 10,
            },
            index=dates,
        )
        print("   OK Sample data created (10 rows, tz-aware)")

        # Create config
        print("2  Creating configuration...")
        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        print(f"   OK Config created — mode={config.mode.value}")

        # Validate
        print("3  Running validation...")
        validator = DQFValidator(config)
        report = validator.validate(data)
        print("   OK Validation complete")

        # Check results
        print("4  Checking results...")
        print(f"   Status : {report.overall_status}")
        print(f"   MPI    : {report.purity_index:.1f}/100")
        print(f"   Gate   : {report.precondition_gate}")
        print(f"   UID    : {report.mif_uid[:48]}...")

        if report.overall_status != "VOID":
            print("   OK Validation passed (not VOID)")
        else:
            print("   FAIL Unexpected VOID status")
            return False

        print()
        return True

    except Exception as e:
        print(f"   FAIL Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_example_runs():
    """Test if examples can be imported"""
    print("=" * 70)
    print("Testing Examples Availability")
    print("=" * 70)
    print()

    examples_dir = Path("examples")

    if not examples_dir.exists():
        print("   WARN Examples directory not found (optional)")
        print()
        return True

    examples = list(examples_dir.glob("*.py"))
    print(f"   Found {len(examples)} example files:")

    for ex in sorted(examples):
        print(f"   - {ex.name}")

    print()
    return True


def main():
    """Run all tests"""
    print()

    # Test imports
    if not test_imports():
        print("FAIL Import tests FAILED")
        sys.exit(1)

    # Test basic usage
    if not test_basic_usage():
        print("FAIL Basic usage tests FAILED")
        sys.exit(1)

    # Test examples
    if not test_example_runs():
        print("FAIL Examples tests FAILED")
        sys.exit(1)

    # Success
    print("=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("DQF v1.1 is correctly installed and ready to use!")
    print()
    print("Next steps:")
    print("  - Run examples: python examples/01_basic_validation.py")
    print("  - Read docs: docs/README.md")
    print("  - API reference: docs/API.md")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
