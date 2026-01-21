"""
DQF - Data Quality Framework for financial OHLCV data

A standalone framework for validating financial time series data quality
before analysis or trading.

Philosophy:
    Without purification, no analysis is trustworthy.
    DQF embodies the principle of ritual purification before sacred practice.

Basic Usage:
    >>> import pandas as pd
    >>> from dqf import DQFValidator, DQFConfig
    >>>
    >>> # Load data
    >>> data = pd.read_csv("btc_usd.csv", index_col=0, parse_dates=True)
    >>>
    >>> # Validate
    >>> validator = DQFValidator(DQFConfig())
    >>> report = validator.validate(data)
    >>>
    >>> print(f"Status: {report.overall_status}")
    >>> print(f"Checks: {report.checks_passed}/{report.total_checks}")

For more information:
    - Documentation: https://github.com/symbioticode/mif-dqf/tree/main/docs
    - Examples: https://github.com/symbioticode/mif-dqf/tree/main/examples
"""

__version__ = "1.0.0"
__author__ = "dravitch"
__email__ = "dravitch@example.com"


# Base classes for custom checks
from dqf.checks.base import BaseCheck, CheckIssue, CheckResult
# Individual checks (for advanced usage)
from dqf.checks.check_1_source import SourceUniquenessCheck
from dqf.checks.check_2_integrity import IntegrityCheck  # CORRECT NAME
from dqf.checks.check_3_calendar import CalendarAlignmentCheck
from dqf.checks.check_4_ffill import ForwardFillCheck  # CORRECT NAME
from dqf.checks.check_5_trace import IndexTraceabilityCheck
from dqf.checks.check_6_sanity import SanityTestsCheck
from dqf.checks.check_7_logging import ComprehensiveLoggingCheck
# Core classes (public API)
from dqf.core.config import DQFConfig
# Enums
from dqf.core.report import DQFReport
from dqf.core.validator import DQFValidator
# Utils (for advanced usage)
from dqf.utils.calendar import detect_calendar, is_weekend  # CORRECT NAMES

# Public API
__all__ = [
    # Version
    "__version__",
    # Core classes (most commonly used)
    "DQFValidator",
    "DQFConfig",
    "DQFReport",
    # Base classes (for custom checks)
    "BaseCheck",
    "CheckResult",
    "CheckIssue",
    "CheckSeverity",
    "CheckStatus",
    # Individual checks (for advanced usage)
    "SourceUniquenessCheck",
    "IntegrityCheck",  #  CORRECT NAME
    "CalendarAlignmentCheck",
    "ForwardFillCheck",  #  CORRECT NAME
    "IndexTraceabilityCheck",
    "SanityTestsCheck",
    "ComprehensiveLoggingCheck",
    # Utils (for advanced usage)
    "detect_calendar",  #  CORRECT NAME
    "is_weekend",  #  CORRECT NAME
]
