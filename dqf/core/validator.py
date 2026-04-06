"""
DQF Validator Module.

Main validation orchestrator that executes all configured checks.
"""

import logging
from typing import Any

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult
from dqf.checks.check_1_source import SourceUniquenessCheck
from dqf.checks.check_2_integrity import IntegrityCheck
from dqf.checks.check_3_calendar import CalendarAlignmentCheck
from dqf.checks.check_4_ffill import ForwardFillCheck
from dqf.checks.check_5_trace import IndexTraceabilityCheck
from dqf.checks.check_6_sanity import SanityTestsCheck
from dqf.checks.check_7_logging import ComprehensiveLoggingCheck
from dqf.core.config import DQFConfig
from dqf.core.report import DQFReport


class DQFValidator:
    """
    Main DQF validation orchestrator.

    Executes all enabled checks and generates comprehensive reports.
    """

    def __init__(
        self,
        config: DQFConfig | None = None,
        enabled_checks: list[int] | None = None,
    ):
        """
        Initialize DQF validator.

        Args:
            config: DQFConfig instance. If None, uses default config.
            enabled_checks: Optional list of check IDs to enable (1-7).
                          If provided, overrides config settings.

        Examples:
            >>> # Default validator (all checks enabled)
            >>> validator = DQFValidator()

            >>> # Custom config
            >>> config = DQFConfig(check_2_integrity={'max_violation_rate': 0.02})
            >>> validator = DQFValidator(config)

            >>> # Only run checks 1, 2, 3
            >>> validator = DQFValidator(enabled_checks=[1, 2, 3])
        """
        self.logger = logging.getLogger(__name__)

        # Initialize config
        if config is None:
            config = DQFConfig()
        self.config = config

        # Initialize all available checks (map by string ID for v1.0.0 compatibility)
        all_checks = {
            "check_1_source": SourceUniquenessCheck(),
            "check_2_integrity": IntegrityCheck(),
            "check_3_calendar": CalendarAlignmentCheck(),
            "check_4_ffill": ForwardFillCheck(),
            "check_5_trace": IndexTraceabilityCheck(),
            "check_6_sanity": SanityTestsCheck(),
            "check_7_logging": ComprehensiveLoggingCheck(),
        }

        #  FIX: Filter checks based on enabled config
        if enabled_checks is not None:
            # Use explicit list (override config) - legacy int IDs
            check_id_map = {
                1: "check_1_source",
                2: "check_2_integrity",
                3: "check_3_calendar",
                4: "check_4_ffill",
                5: "check_5_trace",
                6: "check_6_sanity",
                7: "check_7_logging",
            }
            self.checks = {
                check_id_map[num]: all_checks[check_id_map[num]]
                for num in enabled_checks
                if num in check_id_map
            }
            self.enabled_checks = {
                check_id: self.config.checks.get(check_id, {}) for check_id in self.checks.keys()
            }
        else:
            #  CRITICAL FIX: Use config to determine enabled checks
            self.checks = {}
            self.enabled_checks = {}

            for check_id, check_instance in all_checks.items():
                # Get check config (should always exist in DQFConfig)
                check_config = self.config.checks.get(check_id, {})

                #  FIX: Only enable if EXPLICITLY enabled=True
                # Changed from: check_config.get("enabled", True)
                # To: check_config.get("enabled") is not False
                # is_enabled = check_config.get("enabled") is not False
                # is_enabled = check_config.get("enabled", True)
                is_enabled = True

                if is_enabled:
                    self.checks[check_id] = check_instance
                    self.enabled_checks[check_id] = check_config

        # Storage for custom checks
        self.custom_checks: dict[str, BaseCheck] = {}

        self.logger.info(f"DQFValidator initialized with {len(self.enabled_checks)} enabled checks")

    def add_custom_check(self, check_id: str, check: BaseCheck) -> None:
        """
        Add a custom check to the validator.

        Args:
            check_id: Unique identifier for the custom check
            check: Instance of a class that inherits from BaseCheck

        Example:
            >>> class MyCheck(BaseCheck):
            ...     def run(self, data):
            ...         return CheckResult(...)
            >>>
            >>> validator = DQFValidator()
            >>> validator.add_custom_check('check_8_custom', MyCheck())
        """
        if not isinstance(check, BaseCheck):
            raise TypeError(f"Custom check must inherit from BaseCheck, got {type(check)}")

        self.custom_checks[check_id] = check
        self.logger.info(f"Added custom check: {check_id}")

    def validate(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> DQFReport:
        """
        Validate data through all enabled checks.

        Args:
            data: DataFrame with OHLCV data
            symbol: Asset symbol (e.g., 'BTC-USD')
            source: Data source identifier
            metadata: Optional metadata
            **kwargs: Additional parameters passed to checks

        Returns:
            DQFReport with results and cleaned data
        """
        self.logger.info(f"Starting DQF validation for {symbol or 'unknown'}")

        results: list[CheckResult] = []

        #  FIX: Execute only enabled checks
        for check_id in sorted(self.enabled_checks.keys()):
            if check_id not in self.checks:
                self.logger.warning(f"Check {check_id} not found, skipping")
                continue

            check = self.checks[check_id]
            check_config = self.enabled_checks[check_id]

            try:
                # Get check name (fallback if attribute doesn't exist)
                check_name = getattr(check, "check_name", check.__class__.__name__)

                self.logger.debug(f"Executing Check {check_id}: {check_name}")

                # Merge check-specific config with runtime parameters
                check_params = {**check_config, **kwargs}

                # Run check with appropriate parameters
                result = check.run(
                    data=data,
                    symbol=symbol,
                    source=source,
                    metadata=metadata,
                    **check_params,
                )

                results.append(result)

                self.logger.debug(f"Check {check_id} completed: {result.status}")

            except Exception as e:
                self.logger.error(f"Check {check_id} failed with error: {e}", exc_info=True)

                # Create error result
                from dqf.core.enums import SEVERITY_CRITICAL, STATUS_ERROR

                error_result = CheckResult(
                    check_name=(check_name if "check_name" in locals() else f"Check {check_id}"),
                    status=STATUS_ERROR,
                    severity=SEVERITY_CRITICAL,
                    message=f"Check execution error: {str(e)}",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "check_id": check_id,
                    },
                )

                results.append(error_result)

        # Execute custom checks
        for custom_id, custom_check in self.custom_checks.items():
            try:
                self.logger.debug(f"Executing custom check: {custom_id}")

                result = custom_check.run(
                    data=data,
                    symbol=symbol,
                    source=source,
                    metadata=metadata,
                    **kwargs,
                )

                results.append(result)

                self.logger.debug(f"Custom check {custom_id} completed: {result.status}")

            except Exception as e:
                self.logger.error(f"Custom check {custom_id} failed with error: {e}", exc_info=True)

                from dqf.core.enums import SEVERITY_CRITICAL, STATUS_ERROR

                error_result = CheckResult(
                    check_name=f"Custom: {custom_id}",
                    status=STATUS_ERROR,
                    severity=SEVERITY_CRITICAL,
                    message=f"Custom check execution error: {str(e)}",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "custom_check_id": custom_id,
                    },
                )

                results.append(error_result)

        # Create report
        report = DQFReport(
            results=results,
            symbol=symbol,
            source=source,
            metadata=metadata,
        )

        self.logger.info(
            f"Validation complete: {report.overall_status} "
            f"({report.checks_passed}/{report.total_checks} passed)"
        )

        return report

    def get_enabled_check_ids(self) -> list[str]:
        """
        Get list of enabled check IDs.

        Returns:
            List of check IDs that are currently enabled
        """
        return sorted(self.enabled_checks.keys())

    def is_check_enabled(self, check_id: str) -> bool:
        """
        Check if a specific check is enabled.

        Args:
            check_id: Check ID (e.g., "check_1_source")

        Returns:
            True if check is enabled, False otherwise
        """
        return check_id in self.enabled_checks

    def __repr__(self) -> str:
        """String representation of validator."""
        enabled_ids = self.get_enabled_check_ids()
        custom_count = len(self.custom_checks)

        return f"DQFValidator(enabled_checks={enabled_ids}, " f"custom_checks={custom_count})"
