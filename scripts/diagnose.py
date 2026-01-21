#!/usr/bin/env python3
"""
Diagnose DQF installation issues.

This script performs comprehensive diagnostics to identify
why imports might be failing.
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version"""
    print("🐍 Python Version:")
    print(f"   {sys.version}")
    
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        print("   ✅ Version OK (>=3.10)")
        return True
    else:
        print("   ❌ Version too old (need >=3.10)")
        return False


def check_pythonpath():
    """Check PYTHONPATH"""
    print("\n📍 PYTHONPATH:")
    for path in sys.path:
        print(f"   {path}")
    
    # Check if current directory is in path
    cwd = os.getcwd()
    if cwd in sys.path:
        print(f"   ✅ Current directory in PYTHONPATH")
    else:
        print(f"   ⚠️  Current directory NOT in PYTHONPATH")
        print(f"      Current: {cwd}")


def check_dqf_location():
    """Check where dqf is installed"""
    print("\n📦 DQF Package Location:")
    try:
        import dqf
        print(f"   Location: {dqf.__file__}")
        print(f"   Version: {dqf.__version__}")
        print("   ✅ Package found")
        return True
    except ImportError as e:
        print(f"   ❌ Package not found: {e}")
        return False


def check_file_structure():
    """Check if all files exist"""
    print("\n📁 File Structure:")
    
    required_files = {
        "dqf/__init__.py": "Main package init",
        "dqf/checks/__init__.py": "Checks module init",
        "dqf/checks/base.py": "Base check classes",
        "dqf/core/__init__.py": "Core module init",
        "dqf/core/validator.py": "Validator class",
        "dqf/core/report.py": "Report class",
        "dqf/core/config.py": "Config class",
    }
    
    all_exist = True
    for filepath, description in required_files.items():
        path = Path(filepath)
        if path.exists():
            size = path.stat().st_size
            print(f"   ✅ {filepath} ({size} bytes) - {description}")
        else:
            print(f"   ❌ MISSING: {filepath} - {description}")
            all_exist = False
    
    return all_exist


def check_class_definitions():
    """Check if classes are defined in base.py"""
    print("\n🔍 Checking base.py definitions:")
    
    base_file = Path("dqf/checks/base.py")
    if not base_file.exists():
        print("   ❌ base.py not found")
        return False
    
    content = base_file.read_text()
    
    required_classes = ['CheckResult', 'CheckIssue', 'BaseCheck']
    all_found = True
    
    for cls in required_classes:
        if f"class {cls}" in content:
            print(f"   ✅ class {cls} defined")
        else:
            print(f"   ❌ class {cls} NOT FOUND")
            all_found = False
    
    return all_found


def test_import_sequence():
    """Test imports step by step"""
    print("\n🧪 Testing Import Sequence:")
    
    tests = [
        ("Base classes", "from dqf.checks.base import CheckResult"),
        ("CheckIssue", "from dqf.checks.base import CheckIssue"),
        ("BaseCheck", "from dqf.checks.base import BaseCheck"),
        ("Config", "from dqf.core.config import DQFConfig"),
        ("Report", "from dqf.core.report import DQFReport"),
        ("Validator", "from dqf.core.validator import DQFValidator"),
        ("Top-level", "from dqf import DQFValidator, DQFConfig, DQFReport"),
    ]
    
    all_ok = True
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            all_ok = False
        except Exception as e:
            print(f"   ⚠️  {name}: {type(e).__name__}: {e}")
            all_ok = False
    
    return all_ok


def check_installation_mode():
    """Check if installed in development mode"""
    print("\n⚙️  Installation Mode:")
    
    try:
        import dqf
        dqf_path = Path(dqf.__file__).parent
        cwd = Path.cwd() / "dqf"
        
        if dqf_path.resolve() == cwd.resolve():
            print("   ✅ Installed in development mode (pip install -e .)")
        else:
            print("   ⚠️  Installed in different location")
            print(f"      Package: {dqf_path}")
            print(f"      Source:  {cwd}")
    except ImportError:
        print("   ❌ Package not installed")


def main():
    """Run all diagnostics"""
    print("=" * 70)
    print("DQF Installation Diagnostics")
    print("=" * 70)
    
    results = []
    
    results.append(("Python Version", check_python_version()))
    check_pythonpath()
    results.append(("DQF Location", check_dqf_location()))
    results.append(("File Structure", check_file_structure()))
    results.append(("Class Definitions", check_class_definitions()))
    results.append(("Import Sequence", test_import_sequence()))
    check_installation_mode()
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_ok = all(result for _, result in results)
    
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ ALL DIAGNOSTICS PASSED")
        print("\nDQF should be working correctly!")
        print("If you still have issues, please report with this output.")
    else:
        print("❌ SOME DIAGNOSTICS FAILED")
        print("\nRecommended fixes:")
        print("1. Replace dqf/checks/base.py with version containing CheckIssue")
        print("2. Ensure all __init__.py files exist")
        print("3. Reinstall: pip uninstall dqf -y && pip install -e .[dev]")
    
    print("=" * 70)
    
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()