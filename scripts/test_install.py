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
    print("1️⃣  Testing basic imports...")
    try:
        from dqf import DQFValidator, DQFConfig, DQFReport
        print("   ✅ Core classes imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Base classes
    print("2️⃣  Testing base classes...")
    try:
        from dqf import BaseCheck, CheckResult, CheckIssue
        print("   ✅ Base classes imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 3: Individual checks
    print("3️⃣  Testing individual checks...")
    try:
        from dqf import (
            SourceUniquenessCheck,
            IntegrityCheck,
            CalendarAlignmentCheck,
            ForwardFillCheck,
            IndexTraceabilityCheck,
            SanityTestsCheck,
            ComprehensiveLoggingCheck
        )
        print("   ✅ All 7 checks imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 4: Utils
    print("4️⃣  Testing utils...")
    try:
        from dqf import detect_calendar, is_weekend
        print("   ✅ Utils imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 5: Version
    print("5️⃣  Testing version...")
    try:
        from dqf import __version__
        print(f"   ✅ DQF version: {__version__}")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
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
        from dqf import DQFValidator, DQFConfig
        
        # Create sample data
        print("1️⃣  Creating sample data...")
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'open': [100] * 10,
            'high': [105] * 10,
            'low': [95] * 10,
            'close': [102] * 10,
            'volume': [1000000] * 10
        }, index=dates)
        print("   ✅ Sample data created (10 rows)")
        
        # Create config
        print("2️⃣  Creating configuration...")
        config = DQFConfig()
        print("   ✅ Default config created")
        
        # Validate
        print("3️⃣  Running validation...")
        validator = DQFValidator(config)
        report = validator.validate(data)
        print("   ✅ Validation complete")
        
        # Check results
        print("4️⃣  Checking results...")
        print(f"   Status: {report.overall_status}")
        print(f"   Checks: {report.checks_passed}/{report.total_checks}")
        
        if report.overall_status == "PASS":
            print("   ✅ Validation PASSED")
        else:
            print("   ❌ Validation FAILED")
            return False
        
        print()
        return True
        
    except Exception as e:
        print(f"   ❌ Error during validation: {e}")
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
        print("   ⚠️  Examples directory not found (optional)")
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
        print("❌ Import tests FAILED")
        sys.exit(1)
    
    # Test basic usage
    if not test_basic_usage():
        print("❌ Basic usage tests FAILED")
        sys.exit(1)
    
    # Test examples
    if not test_example_runs():
        print("❌ Examples tests FAILED")
        sys.exit(1)
    
    # Success
    print("=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("DQF is correctly installed and ready to use!")
    print()
    print("Next steps:")
    print("  - Run examples: python examples/01_basic_validation.py")
    print("  - Read docs: docs/README.md")
    print("  - API reference: docs/API.md")
    print()
    
    sys.exit(0)


if __name__ == "__main__":
    main()
