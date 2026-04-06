#!/usr/bin/env python3
"""
DQF Baseline Validator

Verifies the three invariants that must hold before any MIF integration:
  1. Imports work
  2. Linting is clean (no undefined names)
  3. All tests pass
"""

import subprocess
import sys


def run(cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def check_imports() -> bool:
    print("Imports...", end=" ")
    ok, err = run([sys.executable, "-c", "from dqf import DQFValidator, DQFConfig, DQFReport, BaseCheck"])
    print("OK" if ok else f"FAIL\n{err}")
    return ok


def check_linting() -> bool:
    print("Linting...", end=" ")
    ok, err = run(["python", "-m", "ruff", "check", "dqf/", "--select", "F821"])
    print("OK" if ok else f"FAIL\n{err}")
    return ok


def check_tests() -> bool:
    print("Tests...", end=" ")
    ok, out = run([sys.executable, "-m", "pytest", "tests/", "-q", "--no-header", "--tb=short"])
    # Extract summary line
    summary = next((l for l in out.splitlines() if "passed" in l or "failed" in l or "error" in l), out[-200:])
    print(summary if ok else f"FAIL\n{out[-400:]}")
    return ok


def main() -> None:
    print("DQF Baseline")
    print("=" * 40)
    results = [check_imports(), check_linting(), check_tests()]
    print("=" * 40)
    if all(results):
        print("PASS — ready for MIF integration")
    else:
        print("FAIL — fix issues before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()
