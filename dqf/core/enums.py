"""
DQF Enums Module.

Defines standard enums for status and severity levels.
"""

from enum import Enum


class CheckStatus(Enum):
    """
    Standard status values for check results.

    Used to ensure consistency across all checks and tests.
    """

    PASS = "PASS"
    WARNING = "WARNING"  # Note: Tests expect "WARNING", not "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"

    def __str__(self) -> str:
        """Return string value."""
        return self.value


class CheckSeverity(Enum):
    """
    Standard severity levels for issues and check results.

    Used to classify the importance of findings.
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        """Return string value."""
        return self.value


# Convenience constants for backward compatibility
STATUS_PASS = CheckStatus.PASS.value
STATUS_WARNING = CheckStatus.WARNING.value
STATUS_FAIL = CheckStatus.FAIL.value
STATUS_ERROR = CheckStatus.ERROR.value

SEVERITY_INFO = CheckSeverity.INFO.value
SEVERITY_WARNING = CheckSeverity.WARNING.value
SEVERITY_ERROR = CheckSeverity.ERROR.value
SEVERITY_CRITICAL = CheckSeverity.CRITICAL.value
