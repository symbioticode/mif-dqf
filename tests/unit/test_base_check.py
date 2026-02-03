"""
Unit tests for BaseCheck interface

Tests abstract base class behavior and helpers.
"""

import pandas as pd
import pytest

from dqf.checks.base import BaseCheck, CheckResult
from dqf.core.enums import STATUS_FAIL, STATUS_PASS, STATUS_WARNING


class MockCheck(BaseCheck):
    """Mock check for testing BaseCheck interface."""

    def __init__(self):
        """Initialize mock check."""
        super().__init__(check_id="check_99_mock", check_name="Mock Check")

    def run(self, data: pd.DataFrame, **kwargs) -> CheckResult:
        return self._create_result(
            status=STATUS_PASS,
            message="Mock check always passes",
            details={"mock": True},
        )


class TestBaseCheck:
    """Test suite for BaseCheck interface"""

    def test_check_initialization(self):
        """Test check initializes with correct properties."""
        check = MockCheck()

        assert check.check_id == "check_99_mock"
        assert check.check_name == "Mock Check"

    def test_check_id_validation_success(self):
        """Test valid check_id passes validation."""

        class ValidCheck(BaseCheck):
            def __init__(self):
                super().__init__(check_id="check_3_test", check_name="Valid Check")

            def run(self, data, **kwargs):
                pass

        check = ValidCheck()
        assert check.check_id == "check_3_test"

    def test_check_id_validation_failure(self):
        """Test invalid check_id - no longer validates format."""
        # Note: We no longer validate check_id format in v1.0.0
        # Any string is acceptable for extensibility

        class CustomCheck(BaseCheck):
            def __init__(self):
                super().__init__(check_id="custom_check_99", check_name="Custom")

            def run(self, data, **kwargs):
                pass

        check = CustomCheck()
        assert check.check_id == "custom_check_99"

    def test_create_result_helper(self):
        """Test _create_result helper method."""
        check = MockCheck()

        result = check._create_result(
            status=STATUS_WARNING, message="Test warning", details={"key": "value"}
        )

        assert isinstance(result, CheckResult)
        assert result.status == STATUS_WARNING
        assert result.message == "Test warning"
        assert result.check_name == "Mock Check"
        assert result.details["key"] == "value"

    def test_validate_dataframe_success(self, clean_ohlcv_data):
        """Test _validate_dataframe with valid DataFrame."""
        check = MockCheck()

        # Should not raise
        check._validate_dataframe(clean_ohlcv_data)

    def test_validate_dataframe_empty(self, empty_dataframe):
        """Test _validate_dataframe raises on empty DataFrame."""
        check = MockCheck()

        with pytest.raises(ValueError, match="empty"):
            check._validate_dataframe(empty_dataframe)

    # @pytest.mark.xfail(reason="Regex conflict in v1.0.0: pd.DataFrame vs pandas DataFrame")
    def test_validate_dataframe_not_dataframe(self):
        """Test _validate_dataframe raises on non-DataFrame."""
        check = MockCheck()

        with pytest.raises(TypeError, match=r"Expected pd\.DataFrame"):  # (NEW)
            # with pytest.raises(TypeError, match="Expected pd.DataFrame"): (GOOD)
            # The following variant also succeeds, but we keep it commented out to ensure
            # consistency with the integration test suite and the v1.0.0 API expectations.
            # with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            check._validate_dataframe([1, 2, 3])

    def test_check_repr(self):
        """Test check __repr__ method."""
        check = MockCheck()
        repr_str = repr(check)

        assert "MockCheck" in repr_str
        assert "check_99_mock" in repr_str
        assert "Mock Check" in repr_str

    def test_base_check_cannot_instantiate(self):
        """Test BaseCheck cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCheck("test_id", "test_name")


class TestCheckResult:
    """Test suite for CheckResult dataclass"""

    def test_check_result_creation(self):
        """Test CheckResult can be created with all fields."""
        result = CheckResult(
            check_name="test_check",
            status=STATUS_PASS,
            message="Test message",
            details={"key": "value"},
        )

        assert result.check_name == "test_check"
        assert result.status == STATUS_PASS
        assert result.details["key"] == "value"

    def test_check_result_to_dict(self):
        """Test CheckResult serialization to dict - not implemented."""
        # Note: CheckResult is a dataclass, no to_dict() method
        # Use dataclasses.asdict() if needed
        result = CheckResult(
            check_name="test_check",
            status=STATUS_WARNING,
            message="Warning message",
            details={"foo": "bar"},
        )

        assert result.status == STATUS_WARNING
        assert result.details["foo"] == "bar"

    def test_is_passing_pass(self):
        """Test passed property for PASS."""
        result = CheckResult(check_name="test", status=STATUS_PASS, message="", details={})
        assert result.passed is True

    def test_is_passing_warn(self):
        """Test passed property for WARNING."""
        result = CheckResult(check_name="test", status=STATUS_WARNING, message="", details={})
        # WARNING is not "passed" in strict sense
        assert result.passed is False

    def test_is_passing_fail(self):
        """Test failed property for FAIL."""
        result = CheckResult(check_name="test", status=STATUS_FAIL, message="", details={})
        assert result.failed is True

    def test_is_critical_failure(self):
        """Test failed property identifies FAIL status."""
        fail_result = CheckResult(check_name="test", status=STATUS_FAIL, message="", details={})
        pass_result = CheckResult(check_name="test", status=STATUS_PASS, message="", details={})

        assert fail_result.failed is True
        assert pass_result.failed is False
