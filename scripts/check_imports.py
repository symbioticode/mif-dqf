#!/usr/bin/env python3
"""
Check if all imports in dqf/__init__.py are valid.

This script verifies that all files and classes referenced in the
package __init__.py actually exist.
"""

import sys
from pathlib import Path


def check_file_exists(filepath: str) -> bool:
    """Check if a file exists"""
    path = Path(filepath)
    if path.exists():
        print(f"   ✅ {filepath}")
        return True
    else:
        print(f"   ❌ MISSING: {filepath}")
        return False


def main():
    print("=" * 70)
    print("Checking DQF Import Structure")
    print("=" * 70)
    print()
    
    all_ok = True
    
    # Check main package files
    print("1️⃣  Checking main package files:")
    files = [
        "dqf/__init__.py",
        "dqf/py.typed",
    ]
    for f in files:
        if not check_file_exists(f):
            all_ok = False
    print()
    
    # Check core module
    print("2️⃣  Checking core module:")
    files = [
        "dqf/core/__init__.py",
        "dqf/core/config.py",
        "dqf/core/report.py",
        "dqf/core/validator.py",
    ]
    for f in files:
        if not check_file_exists(f):
            all_ok = False
    print()
    
    # Check checks module
    print("3️⃣  Checking checks module:")
    files = [
        "dqf/checks/__init__.py",
        "dqf/checks/base.py",
        "dqf/checks/check_1_source.py",
        "dqf/checks/check_2_integrity.py",
        "dqf/checks/check_3_calendar.py",
        "dqf/checks/check_4_ffill.py",
        "dqf/checks/check_5_trace.py",
        "dqf/checks/check_6_sanity.py",
        "dqf/checks/check_7_logging.py",
    ]
    for f in files:
        if not check_file_exists(f):
            all_ok = False
    print()
    
    # Check utils module
    print("4️⃣  Checking utils module:")
    files = [
        "dqf/utils/__init__.py",
        "dqf/utils/calendar.py",
    ]
    for f in files:
        if not check_file_exists(f):
            all_ok = False
    print()
    
    # Check if imports work
    print("5️⃣  Testing imports:")
    try:
        # Test base classes
        print("   Testing base classes...")
        from dqf.checks.base import BaseCheck, CheckResult, CheckIssue
        print("   ✅ BaseCheck, CheckResult, CheckIssue")
        
        # Test core classes
        print("   Testing core classes...")
        from dqf.core.config import DQFConfig
        from dqf.core.report import DQFReport
        from dqf.core.validator import DQFValidator
        print("   ✅ DQFConfig, DQFReport, DQFValidator")
        
        # Test checks
        print("   Testing individual checks...")
        from dqf.checks.check_1_source import SourceUniquenessCheck
        from dqf.checks.check_2_integrity import IntegrityCheck
        from dqf.checks.check_3_calendar import CalendarAlignmentCheck
        from dqf.checks.check_4_ffill import ForwardFillLimitsCheck
        from dqf.checks.check_5_trace import IndexTraceabilityCheck
        from dqf.checks.check_6_sanity import SanityTestsCheck
        from dqf.checks.check_7_logging import ComprehensiveLoggingCheck
        print("   ✅ All 7 checks")
        
        # Test utils
        print("   Testing utils...")
        from dqf.utils.calendar import detect_trading_calendar, is_trading_day
        print("   ✅ Calendar utils")
        
        # Test top-level imports
        print("   Testing top-level imports...")
        from dqf import DQFValidator, DQFConfig, DQFReport
        print("   ✅ Top-level imports work")
        
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        all_ok = False
    
    print()
    
    # Summary
    print("=" * 70)
    if all_ok:
        print("✅ ALL CHECKS PASSED")
        print("=" * 70)
        print()
        print("Import structure is correct!")
        print("Next: pip install -e .[dev]")
        sys.exit(0)
    else:
        print("❌ SOME CHECKS FAILED")
        print("=" * 70)
        print()
        print("Fix missing files before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()