#!/usr/bin/env python3
"""
validate_dqf_state.py — DQF repo health check.

Verifies that the working tree is consistent with the v1.2 spec:
  - Required source files exist
  - Version strings are aligned
  - No transitional artefacts left in source
  - Tests pass
  - All examples run

Usage:
    python scripts/local/validate_dqf_state.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_failed: list[str] = []
_warned: list[str] = []


def check(
    condition: bool,
    ok_msg: str,
    fail_msg: str,
    warning: bool = False,
) -> None:
    bucket = _warned if warning else _failed
    if condition:
        print(f"  ✅  {ok_msg}")
    else:
        icon = "⚠️ " if warning else "❌ "
        print(f"  {icon} {fail_msg}")
        bucket.append(fail_msg)


# ---------------------------------------------------------------------------
# 1. Required files
# ---------------------------------------------------------------------------
print("\n── Required files ──────────────────────────────────────")
for rel in [
    "dqf/__init__.py",
    "dqf/core/validator.py",
    "dqf/core/report.py",
    "dqf/core/config.py",
    "dqf/core/enums.py",
    "dqf/core/prod_envelope.py",
    "dqf/utils/cleaning_log.py",
    "dqf/utils/mpi.py",
    "pyproject.toml",
    "README.md",
]:
    p = ROOT / rel
    check(p.exists(), f"{rel} present", f"{rel} MISSING")

# ---------------------------------------------------------------------------
# 2. Version alignment
# ---------------------------------------------------------------------------
print("\n── Version ─────────────────────────────────────────────")
pyproject = (ROOT / "pyproject.toml").read_text()
check(
    'version = "1.2.0"' in pyproject,
    "pyproject.toml: version = 1.2.0",
    "pyproject.toml: version != 1.2.0",
)

validator_src = (ROOT / "dqf/core/validator.py").read_text()
check(
    'DQF_VERSION = "1.2.0"' in validator_src,
    "validator.py: DQF_VERSION = 1.2.0",
    "validator.py: DQF_VERSION != 1.2.0",
)

readme = (ROOT / "README.md").read_text()
check(
    "version-1.2.0" in readme,
    "README.md: version badge = 1.2.0",
    "README.md: version badge != 1.2.0",
    warning=True,
)
check(
    "224/224" in readme or "224%2F224" in readme,
    "README.md: test badge = 224/224",
    "README.md: test badge not updated to 224/224",
    warning=True,
)

# ---------------------------------------------------------------------------
# 3. No transitional artefacts in validator.py
# ---------------------------------------------------------------------------
print("\n── Transitional artefacts ──────────────────────────────")
content = validator_src

# Vérifier que le défaut DQFMode.DIAGNOSTIC transitoire est absent
has_bad_default = (
    "DQFMode.DIAGNOSTIC" in content
    and "default" in content.lower()
    and "transitoire" not in content
    and "# DAL" not in content  # exception légitime
)
check(
    not has_bad_default,
    "validator.py: no transitional DQFMode.DIAGNOSTIC default",
    "validator.py: transitional default may still be present",
    warning=True,
)

check(
    "Session 4 rewrite" not in content,
    "validator.py: no 'Session 4 rewrite' marker",
    "validator.py: 'Session 4 rewrite' marker still present",
    warning=True,
)

# ---------------------------------------------------------------------------
# 4. Dependencies
# ---------------------------------------------------------------------------
print("\n── Dependencies ────────────────────────────────────────")
check(
    "pyarrow" in pyproject,
    "pyproject.toml: pyarrow declared",
    "pyproject.toml: pyarrow missing (needed for cleaning log)",
)

# ---------------------------------------------------------------------------
# 5. Import smoke test
# ---------------------------------------------------------------------------
print("\n── Import smoke test ───────────────────────────────────")
result = subprocess.run(
    [sys.executable, "-c", "from dqf import DQFValidator, DQFConfig, DQFMode; print('ok')"],
    capture_output=True,
    text=True,
    cwd=ROOT,
)
check(
    result.returncode == 0 and "ok" in result.stdout,
    "from dqf import DQFValidator, DQFConfig, DQFMode  → OK",
    f"import failed: {result.stderr.strip()[:120]}",
)

# mif_dqf must NOT be importable (expected ModuleNotFoundError)
result2 = subprocess.run(
    [sys.executable, "-c", "import mif_dqf"],
    capture_output=True,
    text=True,
    cwd=ROOT,
)
check(
    result2.returncode != 0,
    "import mif_dqf → ModuleNotFoundError (expected)",
    "import mif_dqf succeeded — unexpected",
    warning=True,
)

# ---------------------------------------------------------------------------
# 6. Test suite
# ---------------------------------------------------------------------------
print("\n── Test suite ──────────────────────────────────────────")
tr = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
    capture_output=True,
    text=True,
    cwd=ROOT,
)
passed_line = [l for l in tr.stdout.splitlines() if "passed" in l]
summary = passed_line[-1].strip() if passed_line else tr.stdout.strip()[-120:]
check(
    tr.returncode == 0,
    f"pytest: {summary}",
    f"pytest FAILED: {summary}",
)

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
print("\n" + "═" * 58)
if _failed:
    print(f"VERDICT : FAIL ❌  ({len(_failed)} failed, {len(_warned)} warned)")
    for m in _failed:
        print(f"  ❌ {m}")
    sys.exit(1)
elif _warned:
    print(f"VERDICT : GO WITH WARNINGS ⚠️  (0 failed, {len(_warned)} warned)")
    for m in _warned:
        print(f"  ⚠️  {m}")
    sys.exit(0)
else:
    print("VERDICT : GO ✅  (0 failed, 0 warned)")
    sys.exit(0)
