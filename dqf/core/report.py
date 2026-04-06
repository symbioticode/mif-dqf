"""
DQF Report Module.

Generates comprehensive validation reports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from dqf.checks.base import CheckResult
from dqf.core.enums import STATUS_ERROR, STATUS_FAIL, STATUS_PASS, STATUS_WARNING

timestamp = datetime.now(timezone.utc).isoformat()


class DQFReport:
    """
    Comprehensive validation report.

    Aggregates results from all checks and provides summary statistics.
    """

    def __init__(
        self,
        results: list[CheckResult],
        symbol: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize validation report.

        Args:
            results: List of CheckResult objects from validation
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
        """
        self.results = results
        self.symbol = symbol
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

        # Calculate summary statistics
        self._calculate_summary()

    def _calculate_summary(self) -> None:
        """Calculate summary statistics from results."""
        self.total_checks = len(self.results)
        self.checks_passed = sum(1 for r in self.results if r.status == STATUS_PASS)
        self.checks_failed = sum(1 for r in self.results if r.status == STATUS_FAIL)
        self.checks_warning = sum(1 for r in self.results if r.status == STATUS_WARNING)
        self.checks_error = sum(1 for r in self.results if r.status == STATUS_ERROR)

        # Determine overall status
        if self.checks_error > 0 or self.checks_failed > 0:
            self.overall_status = STATUS_FAIL
        elif self.checks_warning > 0:
            self.overall_status = STATUS_WARNING
        else:
            self.overall_status = STATUS_PASS

    def to_dict(self) -> dict[str, Any]:
        """
        Export report to dictionary.

        Returns:
            Dictionary representation of report
        """
        return {
            "report_metadata": {
                "timestamp": self.timestamp,
                "symbol": self.symbol,
                "source": self.source,
                "metadata": self.metadata,
            },
            "summary": {
                "overall_status": self.overall_status,
                "total_checks": self.total_checks,
                "checks_passed": self.checks_passed,
                "checks_failed": self.checks_failed,
                "checks_warning": self.checks_warning,
                "checks_error": self.checks_error,
            },
            "results": [
                {
                    "check_name": r.check_name,
                    "status": r.status,
                    "severity": r.severity,
                    "message": r.message,
                    "details": r.details,
                    "issues": (
                        [
                            {
                                "severity": issue.severity,
                                "message": issue.message,
                                "location": issue.location,
                                "details": issue.details,
                            }
                            for issue in r.issues
                        ]
                        if r.issues
                        else []
                    ),
                }
                for r in self.results
            ],
        }

    def to_yaml(self, filepath: str | None = None) -> str | None:
        """
        Export report to YAML format.

        Args:
            filepath: Optional path to save YAML file. If None, returns string.

        Returns:
            YAML string if filepath is None, otherwise None
        """
        report_dict = self.to_dict()
        yaml_str = yaml.dump(report_dict, default_flow_style=False, sort_keys=False)

        if filepath:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(yaml_str)
            return None

        return yaml_str

    def to_json(self, filepath: str | None = None, indent: int = 2) -> str | None:
        """
        Export report to JSON format.

        Args:
            filepath: Optional path to save JSON file. If None, returns string.
            indent: Number of spaces for indentation

        Returns:
            JSON string if filepath is None, otherwise None
        """
        report_dict = self.to_dict()
        json_str = json.dumps(report_dict, indent=indent)

        if filepath:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(json_str)
            return None

        return json_str

    def print_summary(self) -> None:
        """Print human-readable summary to console."""
        print("=" * 70)
        print("DQF VALIDATION REPORT")
        print("=" * 70)
        print(f"\nSymbol: {self.symbol or 'N/A'}")
        print(f"Source: {self.source or 'N/A'}")
        print(f"Timestamp: {self.timestamp}")
        print(f"\nOverall Status: {self.overall_status}")
        print("\nSummary:")
        print(f"  Total Checks: {self.total_checks}")
        print(f"   Passed: {self.checks_passed}")
        print(f"    Warning: {self.checks_warning}")
        print(f"   Failed: {self.checks_failed}")
        print(f"   Error: {self.checks_error}")
        print("\n" + "=" * 70)
        print("Check Results:")
        print("=" * 70)

        for i, result in enumerate(self.results, 1):
            status_icon = {
                STATUS_PASS: "",
                STATUS_WARNING: "",
                STATUS_FAIL: "",
                STATUS_ERROR: "",
            }.get(result.status, "")

            print(f"\n{i}. {status_icon} {result.check_name}")
            print(f"   Status: {result.status}")
            print(f"   Message: {result.message}")

            if result.issues:
                print(f"   Issues: {len(result.issues)}")
                for issue in result.issues[:3]:  # Show first 3 issues
                    print(f"     - {issue.message}")
                if len(result.issues) > 3:
                    print(f"     ... and {len(result.issues) - 3} more")

        print("\n" + "=" * 70)

    def get_failed_checks(self) -> list[CheckResult]:
        """
        Get list of failed checks.

        Returns:
            List of CheckResult objects with FAIL or ERROR status
        """
        return [r for r in self.results if r.status in {STATUS_FAIL, STATUS_ERROR}]

    def get_warning_checks(self) -> list[CheckResult]:
        """
        Get list of checks with warnings.

        Returns:
            List of CheckResult objects with WARNING status
        """
        return [r for r in self.results if r.status == STATUS_WARNING]

    def get_passed_checks(self) -> list[CheckResult]:
        """
        Get list of passed checks.

        Returns:
            List of CheckResult objects with PASS status
        """
        return [r for r in self.results if r.status == STATUS_PASS]

    def is_valid(self) -> bool:
        """
        Check if validation passed overall.

        Returns:
            True if overall_status is PASS, False otherwise
        """
        return self.overall_status == STATUS_PASS

    def has_warnings(self) -> bool:
        """
        Check if there are any warnings.

        Returns:
            True if there are warnings, False otherwise
        """
        return self.checks_warning > 0

    def has_errors(self) -> bool:
        """
        Check if there are any errors or failures.

        Returns:
            True if there are errors/failures, False otherwise
        """
        return (self.checks_failed + self.checks_error) > 0

    @property
    def all_issues(self) -> list[Any]:
        """
        Get all issues from all check results.

        Returns:
            Flattened list of all CheckIssue objects from all results
        """
        issues = []
        for result in self.results:
            if result.issues:
                issues.extend(result.issues)
        return issues

    @property
    def check_results(self) -> dict[str, CheckResult]:
        """
        Get check results as a dictionary keyed by check name.

        Returns:
            Dictionary mapping check names to CheckResult objects
        """
        return {result.check_name: result for result in self.results}

    def __repr__(self) -> str:
        """String representation of report."""
        return (
            f"DQFReport(status={self.overall_status}, "
            f"passed={self.checks_passed}/{self.total_checks})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"DQF Report: {self.overall_status} ({self.checks_passed}/{self.total_checks} passed)"
        )
