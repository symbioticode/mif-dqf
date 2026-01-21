#!/usr/bin/env python3
"""
Verify that all class names in dqf/__init__.py match actual implementations.

This script checks that every import in __init__.py refers to a class
that actually exists in the corresponding module.
"""

import sys
import importlib.util
from pathlib import Path


def check_class_exists(module_path: str, class_name: str) -> bool:
    """Check if a class exists in a module"""
    try:
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        if spec is None or spec.loader is None:
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return hasattr(module, class_name)
    except Exception as e:
        print(f"   ⚠️  Error loading {module_path}: {e}")
        return False


def main():
    print("=" * 70)
    print("Verifying Class Names in dqf/__init__.py")
    print("=" * 70)
    print()
    
    # Checks to verify
    checks = [
        ("dqf/checks/check_1_source.py", "SourceUniquenessCheck"),
        ("dqf/checks/check_2_integrity.py", "IntegrityCheck"),
        ("dqf/checks/check_3_calendar.py", "CalendarAlignmentCheck"),
        ("dqf/checks/check_4_ffill.py", "ForwardFillCheck"),
        ("dqf/checks/check_5_trace.py", "IndexTraceabilityCheck"),
        ("dqf/checks/check_6_sanity.py", "SanityTestsCheck"),
        ("dqf/checks/check_7_logging.py", "ComprehensiveLoggingCheck"),
    ]
    
    print("🔍 Checking individual checks:")
    all_ok = True
    
    for module_path, class_name in checks:
        if Path(module_path).exists():
            if check_class_exists(module_path, class_name):
                print(f"   ✅ {class_name} exists in {module_path}")
            else:
                print(f"   ❌ {class_name} NOT FOUND in {module_path}")
                all_ok = False
        else:
            print(f"   ❌ File not found: {module_path}")
            all_ok = False
    
    print()
    
    # Utils to verify
    utils = [
        ("dqf/utils/calendar.py", "detect_calendar"),
        ("dqf/utils/calendar.py", "is_weekend"),
    ]
    
    print("🔍 Checking utils:")
    
    for module_path, func_name in utils:
        if Path(module_path).exists():
            if check_class_exists(module_path, func_name):
                print(f"   ✅ {func_name} exists in {module_path}")
            else:
                print(f"   ❌ {func_name} NOT FOUND in {module_path}")
                all_ok = False
        else:
            print(f"   ❌ File not found: {module_path}")
            all_ok = False
    
    print()
    
    # Core classes
    core = [
        ("dqf/core/config.py", "DQFConfig"),
        ("dqf/core/report.py", "DQFReport"),
        ("dqf/core/validator.py", "DQFValidator"),
    ]
    
    print("🔍 Checking core classes:")
    
    for module_path, class_name in core:
        if Path(module_path).exists():
            if check_class_exists(module_path, class_name):
                print(f"   ✅ {class_name} exists in {module_path}")
            else:
                print(f"   ❌ {class_name} NOT FOUND in {module_path}")
                all_ok = False
        else:
            print(f"   ❌ File not found: {module_path}")
            all_ok = False
    
    print()
    print("=" * 70)
    
    if all_ok:
        print("✅ ALL CLASS NAMES VERIFIED")
        print("=" * 70)
        print()
        print("All imports in dqf/__init__.py should work correctly!")
        sys.exit(0)
    else:
        print("❌ SOME CLASS NAMES ARE INCORRECT")
        print("=" * 70)
        print()
        print("Fix the class names in dqf/__init__.py before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()