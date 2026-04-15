"""
Base classes for DQF checks.

Defines abstract base class and result types for all validation checks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from dqf.core.enums import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STATUS_ERROR,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SKIP,
    STATUS_WARN,
)
from dqf.utils.mpi import InterventionLog


@dataclass
class CheckIssue:
    """
    Represents a single issue found during validation.

    Attributes:
        severity: Issue severity ('ERROR', 'WARNING', 'INFO')
        message: Human-readable description
        location: Where the issue occurred (row, column, etc.)
        details: Additional context
    """

    severity: str
    message: str
    location: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class CheckResult:
    """
    Result of a single validation check.

    Attributes:
        check_name: Name of the check that produced this result
        status: Per-check status — 'PASS', 'FAIL', 'WARN', 'SKIP', 'ERROR'
        message: Summary message
        issues: List of specific issues found
        details: Additional metadata
        severity: Overall severity level
        interventions: Interventions performed by this check (v1.1).
            Populated by checks that modify or detect data requiring
            correction. Aggregated by DQFValidator to compute the MPI.
    """

    check_name: str = "UnknownCheck"
    status: str = "PASS"
    message: str = ""
    issues: list[CheckIssue] = field(default_factory=list)
    details: dict[str, Any] | None = None
    severity: str = "INFO"
    interventions: InterventionLog | None = None
    cleaning_entries: list[dict] = field(default_factory=list)
    # cleaning_entries: per-row detail dicts for CleaningLog (v1.2).
    # Populated by checks that detect interventions. Aggregated by
    # DQFValidator when enable_cleaning_log=True.

    def __post_init__(self):
        """Validate result after initialization."""
        # v1.1 vocabulary: WARN replaces WARNING at the per-check level.
        # STATUS_WARNING ("WARNING") is the overall manifest status; it is
        # not a valid per-check result status.
        valid_statuses = {STATUS_PASS, STATUS_WARN, STATUS_SKIP, STATUS_FAIL, STATUS_ERROR}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {valid_statuses}")

        valid_severities = {
            SEVERITY_INFO,
            SEVERITY_WARNING,
            SEVERITY_ERROR,
            SEVERITY_CRITICAL,
        }
        if self.severity not in valid_severities:
            raise ValueError(
                f"Invalid severity '{self.severity}'. Must be one of {valid_severities}"
            )

    @property
    def passed(self) -> bool:
        """Check if validation passed."""
        return self.status == STATUS_PASS

    @property
    def failed(self) -> bool:
        """Check if validation failed."""
        return self.status in {STATUS_FAIL, STATUS_ERROR}

    def add_issue(
        self,
        severity: str,
        message: str,
        location: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Add an issue to this result.

        Args:
            severity: Issue severity
            message: Issue description
            location: Where issue occurred
            details: Additional context
        """
        issue = CheckIssue(
            severity=severity,
            message=message,
            location=location,
            details=details,
        )
        self.issues.append(issue)


class BaseCheck(ABC):
    """
    Abstract base class for all DQF validation checks.

    All checks must inherit from this class and implement the run() method.
    This enriched version provides attributes and helper methods expected by tests.
    """

    def __init__(self, check_id: str, check_name: str) -> None:
        """
        Initialize base check with ID and name.

        Args:
            check_id: Unique identifier for this check (e.g., 'check_1_source')
            check_name: Human-readable name (e.g., 'Source Uniqueness')
        """
        self.check_id = check_id
        self.check_name = check_name

    @abstractmethod
    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> CheckResult:
        """
        Execute the validation check.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata
            **kwargs: Additional check-specific parameters

        Returns:
            CheckResult with validation outcome
        """
        pass

    '''
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate that input is a proper DataFrame.

        Args:
            df: Object to validate

        Raises:
            TypeError: If df is not a pandas DataFrame
            ValueError: If DataFrame is empty
        """
        #if not isinstance(df, pd.DataFrame):
        #   raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")
        #    raise TypeError(f"Expected pd.DataFrame, got {type(df).__name__}")

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame (pd.DataFrame), got {type(df).__name__}"
            )

        if df.empty:
            raise ValueError("DataFrame cannot be empty")
    '''

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate that input is a proper DataFrame.

        Args:
            df: Object to validate

        Raises:
            TypeError: If df is not a pandas DataFrame
            ValueError: If DataFrame is empty
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                # f"Expected pandas DataFrame (pd.DataFrame), got {type(df).__name__}"
                # f"Expected pd.DataFrame (pandas DataFrame), got {type(df).__name__}" (GOOD)
                f"Expected pd.DataFrame, got {type(df).__name__}"  # (NEW)
            )
            # raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")
            # raise TypeError(f"Expected pd.DataFrame, got {type(df).__name__}")   #(NEW)

        if df.empty:
            raise ValueError("DataFrame cannot be empty")

    def _create_result(
        self,
        status: str,
        message: str = "",
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
    ) -> CheckResult:
        """
        Helper to create a CheckResult with consistent formatting.

        Args:
            status: Result status ('PASS', 'FAIL', 'WARNING', 'ERROR')
            message: Summary message
            severity: Overall severity level
            details: Additional metadata
            issues: List of specific issues

        Returns:
            CheckResult instance

        Example:
            >>> result = self._create_result(
            ...     status='FAIL',
            ...     message='Found 5 integrity violations',
            ...     severity='ERROR',
            ...     details={'violation_count': 5}
            ... )
        """
        return CheckResult(
            check_name=self.check_name,
            status=status,
            message=message,
            severity=severity,
            details=details or {},
        )

    def _create_pass_result(self, message: str = "Check passed", **kwargs) -> CheckResult:
        """
        Convenience method to create a passing result.

        Args:
            message: Success message
            **kwargs: Additional arguments passed to _create_result

        Returns:
            CheckResult with PASS status
        """
        return self._create_result(
            status=STATUS_PASS,
            message=message,
            severity=SEVERITY_INFO,
            **kwargs,
        )

    def _create_fail_result(
        self,
        message: str,
        severity: str = SEVERITY_ERROR,
        **kwargs,
    ) -> CheckResult:
        """
        Convenience method to create a failing result.

        Args:
            message: Failure message
            severity: Severity level (default: ERROR)
            **kwargs: Additional arguments passed to _create_result

        Returns:
            CheckResult with FAIL status
        """
        return self._create_result(
            status=STATUS_FAIL,
            message=message,
            severity=severity,
            **kwargs,
        )

    def _create_warning_result(self, message: str, **kwargs) -> CheckResult:
        """
        Convenience method to create a warning result.

        Args:
            message: Warning message
            **kwargs: Additional arguments passed to _create_result

        Returns:
            CheckResult with WARN status (v1.1 per-check vocabulary)
        """
        return self._create_result(
            status=STATUS_WARN,
            message=message,
            severity=SEVERITY_WARNING,
            **kwargs,
        )

    def _create_error_result(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> CheckResult:
        """
        Convenience method to create an error result (for exceptions).

        Args:
            message: Error message
            exception: Optional exception that caused the error
            **kwargs: Additional arguments passed to _create_result

        Returns:
            CheckResult with ERROR status
        """
        details = kwargs.pop("details", {})

        if exception:
            details["error"] = str(exception)
            details["error_type"] = type(exception).__name__

        return self._create_result(
            status=STATUS_ERROR,
            message=message,
            severity=SEVERITY_CRITICAL,
            details=details,
            **kwargs,
        )

    def _validate_ohlcv_columns(self, df: pd.DataFrame, required: list[str] | None = None) -> None:
        """
        Validate that DataFrame has required OHLCV columns.

        Args:
            df: DataFrame to validate
            required: List of required column names.
                     Defaults to ['open', 'high', 'low', 'close', 'volume']

        Raises:
            ValueError: If required columns are missing
        """
        if required is None:
            required = ["open", "high", "low", "close", "volume"]

        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(
                f"Missing required OHLCV columns: {missing}. " f"Found columns: {list(df.columns)}"
            )

    def _validate_datetime_index(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame has a datetime index.

        Args:
            df: DataFrame to validate

        Raises:
            TypeError: If index is not DatetimeIndex
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise TypeError(f"Expected DatetimeIndex, got {type(df.index).__name__}")

    def __repr__(self) -> str:
        """String representation of check."""
        return f"{self.__class__.__name__}(id='{self.check_id}', name='{self.check_name}')"
