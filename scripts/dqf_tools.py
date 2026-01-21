#!/usr/bin/env python3
"""
DQF Tools - Unified tooling script

Consolidates: fix_encoding.py, check_encoding.py, doctor.py, cleanup.sh

Usage:
    python scripts/dqf_tools.py check-encoding
    python scripts/dqf_tools.py fix-encoding
    python scripts/dqf_tools.py doctor
    python scripts/dqf_tools.py cleanup
"""

import sys
import pathlib
import subprocess
from typing import List, Tuple


# === ENCODING UTILITIES ===

def scan_non_ascii(paths: List[str]) -> List[Tuple[str, int, int]]:
    """Scan files for non-ASCII characters."""
    issues = []
    
    for path_str in paths:
        for file_path in pathlib.Path(path_str).rglob("*.py"):
            content = file_path.read_bytes()
            
            for i, byte in enumerate(content):
                if byte > 127:
                    line = content[:i].count(b'\n') + 1
                    issues.append((str(file_path), line, byte))
    
    return issues


def check_encoding():
    """Check for non-ASCII characters in Python files."""
    print("🔍 Checking encoding...")
    
    issues = scan_non_ascii(["dqf", "tests"])

    # Check justfile
    jf = pathlib.Path("justfile")
    if jf.exists():
        content = jf.read_bytes()
        if any(b > 127 for b in content):
            issues.append(("justfile", 0, "non-ascii"))
    
    if issues:
        print(f"❌ Found {len(issues)} non-ASCII characters:")
        for filepath, line, byte in issues[:10]:
            print(f"   {filepath}:{line} - byte {byte}")
        sys.exit(1)
    else:
        print("✅ All files ASCII-only")
        sys.exit(0)


def fix_encoding():
    """Fix non-ASCII characters in Python files."""
    print("🧹 Fixing encoding...")
    
    fixed = []
    
    # Python files
    for path_str in ["dqf", "tests"]:
        for file_path in pathlib.Path(path_str).rglob("*.py"):
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            ascii_content = content.encode("ascii", errors="ignore").decode("ascii")
            
            if content != ascii_content:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                file_path.write_text(content, encoding="utf-8")
                backup_path.write_text(content, encoding="utf-8")
                file_path.write_text(ascii_content, encoding="ascii")
                fixed.append(str(file_path))

    # Justfile
    jf = pathlib.Path("justfile")
    if jf.exists():
        content = jf.read_text(encoding="utf-8", errors="ignore")
        ascii_content = content.encode("ascii", errors="ignore").decode("ascii")

        if content != ascii_content:
            backup_path = jf.with_suffix(jf.suffix + ".bak")
            jf.write_text(content, encoding="utf-8")
            backup_path.write_text(content, encoding="utf-8")
            jf.write_text(ascii_content, encoding="ascii")
            fixed.append("justfile")
    
    if fixed:
        print(f"✅ Fixed {len(fixed)} files:")
        for f in fixed:
            print(f"   - {f}")
    else:
        print("✅ No non-ASCII characters found")
    sys.exit(0)


# === DOCTOR UTILITIES ===

def doctor():
    """Health check for DQF project."""
    print("🩺 DQF DOCTOR CHECK")
    print("=" * 60)
    
    problems = []
    
    # Check 1: ASCII encoding
    print("\n1. Checking encoding...")
    ascii_issues = scan_non_ascii(["dqf", "tests"])
    if ascii_issues:
        problems.append(f"Non-ASCII characters: {len(ascii_issues)} found")
        print(f"   ❌ {len(ascii_issues)} non-ASCII characters")
    else:
        print("   ✅ All files ASCII-only")
    
    # Check 2: Empty files
    print("\n2. Checking for empty files...")
    empty_files = []
    for file_path in pathlib.Path("dqf").rglob("*.py"):
        if file_path.stat().st_size == 0 or file_path.read_text().strip() == "":
            empty_files.append(str(file_path))
    
    if empty_files:
        problems.append(f"Empty files: {', '.join(empty_files)}")
        print(f"   ❌ {len(empty_files)} empty files")
    else:
        print("   ✅ No empty files")
    
    # Check 3: __pycache__ artifacts
    print("\n3. Checking for artifacts...")
    pycache_dirs = list(pathlib.Path(".").rglob("__pycache__"))
    if pycache_dirs:
        print(f"   ⚠️  {len(pycache_dirs)} __pycache__ directories (run 'just clean')")
    else:
        print("   ✅ No __pycache__ artifacts")
    
    # Check 4: Backup files
    print("\n4. Checking for backup files...")
    backup_files = list(pathlib.Path(".").rglob("*.bak")) + list(pathlib.Path(".").rglob("*.bkp"))
    if backup_files:
        print(f"   ⚠️  {len(backup_files)} backup files (run 'just cleanup')")
    else:
        print("   ✅ No backup files")
    
    # Check 5: Tests pass
    print("\n5. Running tests...")
    result = subprocess.run(["pytest", "tests/", "-q"], capture_output=True)
    if result.returncode == 0:
        print("   ✅ All tests pass")
    else:
        problems.append("Tests failing")
        print("   ❌ Tests failing (run 'just test')")
    
    # Summary
    print("\n" + "=" * 60)
    if problems:
        print("❌ ISSUES FOUND:")
        for p in problems:
            print(f"   - {p}")
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED")
        sys.exit(0)


# === CLEANUP UTILITIES ===

def cleanup():
    """Run cleanup.sh script."""
    print("🧹 Running cleanup...")
    
    cleanup_script = pathlib.Path("scripts/cleanup.sh")
    
    if not cleanup_script.exists():
        print("❌ cleanup.sh not found")
        sys.exit(1)
    
    result = subprocess.run(["bash", str(cleanup_script)])
    sys.exit(result.returncode)


# === MAIN ===

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: dqf_tools.py <command>")
        print("\nCommands:")
        print("  check-encoding  - Check for non-ASCII characters")
        print("  fix-encoding    - Fix non-ASCII characters")
        print("  doctor          - Run health checks")
        print("  cleanup         - Run cleanup script")
        sys.exit(1)
    
    command = sys.argv[1]
    
    commands = {
        "check-encoding": check_encoding,
        "fix-encoding": fix_encoding,
        "doctor": doctor,
        "cleanup": cleanup,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)
    
    commands[command]()


if __name__ == "__main__":
    main()