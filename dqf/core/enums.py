"""
DQF Enums Module — v1.1

Single source of truth for all DQF constants:
  - DQFMode         : operational modes (CERTIFICATION / DIAGNOSTIC)
  - CheckStatus     : per-check result statuses
  - CheckSeverity   : issue severity levels
  - Overall statuses: CERTIFIED, WARNING, VOID, FAIL
  - PRECONDITION_GATE: DQF → MIF gate mapping (spec §7)
"""

from enum import Enum


class DQFMode(Enum):
    """
    Operational mode for DQF validation.

    CERTIFICATION : All MIF-CORE checks active and non-bypassable.
                    Calendar must be explicitly declared.
                    Used by MIF to certify a metric under controlled conditions.

    DIAGNOSTIC    : MIF-ADVISORY checks configurable, calendar auto-detection
                    permitted. Used by practitioners to assess data quality.
                    Results carry annotation: not eligible for MIF certification.
    """

    CERTIFICATION = "CERTIFICATION"
    DIAGNOSTIC = "DIAGNOSTIC"

    def __str__(self) -> str:
        return self.value


class CheckStatus(Enum):
    """
    Per-check result statuses (v1.1).

    PASS  : Check passed with no issues.
    FAIL  : Check failed — for CORE checks, triggers VOID overall status.
    WARN  : Advisory threshold exceeded — non-blocking.
    SKIP  : Check not run (e.g. C1 in Phase 1, DAL-pending).
    ERROR : Unexpected exception during check execution.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


class CheckSeverity(Enum):
    """
    Severity levels for issues and check results.
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Overall validation status constants (DQFReport.overall_status)
# ---------------------------------------------------------------------------

STATUS_CERTIFIED = "CERTIFIED"  # All CORE checks PASS
STATUS_WARNING = "WARNING"  # CORE PASS, at least one ADVISORY WARN
STATUS_VOID = "VOID"  # At least one CORE FAIL or bypass — gate = 0.0
STATUS_FAIL = "FAIL"  # Unexpected pipeline error

# ---------------------------------------------------------------------------
# Per-check status constants (CheckResult.status)
# ---------------------------------------------------------------------------

STATUS_PASS = CheckStatus.PASS.value
STATUS_WARN = CheckStatus.WARN.value
STATUS_SKIP = CheckStatus.SKIP.value
STATUS_ERROR = CheckStatus.ERROR.value
# STATUS_FAIL already defined above — same value "FAIL", shared by both scopes

# ---------------------------------------------------------------------------
# Severity constants (convenience aliases)
# ---------------------------------------------------------------------------

SEVERITY_INFO = CheckSeverity.INFO.value
SEVERITY_WARNING = CheckSeverity.WARNING.value
SEVERITY_ERROR = CheckSeverity.ERROR.value
SEVERITY_CRITICAL = CheckSeverity.CRITICAL.value

# ---------------------------------------------------------------------------
# precondition_gate mapping (spec §7)
# Maps DQFReport.overall_status → float gate value applied to MIF scores.
#
# VOID    : 0.0  — CORE check bypassed or failed; MIF score zeroed
# FAIL    : 0.2  — unexpected pipeline error
# WARNING : 0.8  — advisory threshold exceeded (further capped by MPI)
# CERTIFIED: 1.0 — full certification, no cap
# ---------------------------------------------------------------------------

PRECONDITION_GATE: dict[str, float] = {
    STATUS_CERTIFIED: 1.0,
    STATUS_WARNING: 0.8,
    STATUS_FAIL: 0.2,
    STATUS_VOID: 0.0,
}
