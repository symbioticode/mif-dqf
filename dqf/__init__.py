"""
DQF - Data Quality Framework for financial OHLCV data

A standalone framework for validating financial time series data quality
before analysis or trading. Produces MIF-Lite manifests (.mif.json) with
a cryptographic MIF-UID and a MIF Purity Index (MPI).

Philosophy:
    Without purification, no analysis is trustworthy.
    DQF embodies the principle of ritual purification before sacred practice.

Basic Usage:
    >>> import pandas as pd
    >>> from dqf import DQFValidator, DQFConfig, DQFMode
    >>>
    >>> # Load data
    >>> data = pd.read_csv("btc_usd.csv", index_col=0, parse_dates=True)
    >>>
    >>> # Validate
    >>> config = DQFConfig(mode=DQFMode.CERTIFICATION)
    >>> validator = DQFValidator(config)
    >>> report = validator.validate(data, calendar="NYSE")
    >>>
    >>> if report.is_certified:
    ...     print(f"MPI: {report.purity_index:.1f}/100")
    ... else:
    ...     print(f"Status: {report.overall_status}, gate={report.precondition_gate}")

For more information:
    - Documentation: https://github.com/symbioticode/mif-dqf/tree/main/docs
    - Examples: https://github.com/symbioticode/mif-dqf/tree/main/examples
"""

__version__ = "1.1.0"
__author__ = "dravitch"
__email__ = "dravitch@example.com"


# Base classes for custom checks
from dqf.checks.base import BaseCheck, CheckIssue, CheckResult

# Individual checks (for advanced usage)
from dqf.checks.check_1_source import SourceUniquenessCheck
from dqf.checks.check_2_integrity import IntegrityCheck
from dqf.checks.check_3_calendar import CalendarAlignmentCheck
from dqf.checks.check_4_ffill import ForwardFillCheck
from dqf.checks.check_5_trace import IndexTraceabilityCheck

# Core classes (public API)
from dqf.core.config import DQFConfig
from dqf.core.enums import DQFMode
from dqf.core.prod_envelope import PRODEnvelope
from dqf.core.report import DQFReport
from dqf.core.validator import DQFValidator

# Utils (for advanced usage)
from dqf.utils.calendar import detect_calendar, is_weekend
from dqf.utils.mpi import InterventionLog, compute_mpi

# Public API
__all__ = [
    # Version
    "__version__",
    # Core classes (most commonly used)
    "DQFValidator",
    "DQFConfig",
    "DQFReport",
    "DQFMode",
    # PROD Envelope (MIF-Lite manifest builder)
    "PRODEnvelope",
    # MPI utilities
    "InterventionLog",
    "compute_mpi",
    # Base classes (for custom checks)
    "BaseCheck",
    "CheckResult",
    "CheckIssue",
    # Individual checks (for advanced usage)
    "SourceUniquenessCheck",
    "IntegrityCheck",
    "CalendarAlignmentCheck",
    "ForwardFillCheck",
    "IndexTraceabilityCheck",
    # Utils (for advanced usage)
    "detect_calendar",
    "is_weekend",
]
