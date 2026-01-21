# test_debug_validator.py
import pandas as pd
from dqf.core.config import DQFConfig
from dqf.core.validator import DQFValidator

# Data simple
dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
data = pd.DataFrame({
    "open": range(100, 110),
    "high": range(105, 115),
    "low": range(95, 105),
    "close": range(102, 112),
    "volume": [1000] * 10,
}, index=dates)

# Config avec 3 checks enabled
config = DQFConfig()
config.checks["check_1_source"]["enabled"] = True
config.checks["check_2_integrity"]["enabled"] = True
config.checks["check_3_calendar"]["enabled"] = True
config.checks["check_4_ffill"]["enabled"] = False
config.checks["check_5_trace"]["enabled"] = False
config.checks["check_6_sanity"]["enabled"] = False
config.checks["check_7_logging"]["enabled"] = False

# DEBUG PRINTS
print("\n=== DEBUG CONFIG ===")
for check_id, check_config in config.checks.items():
    enabled = check_config.get("enabled", True)
    print(f"{check_id}: enabled={enabled}")

# Créer validator
validator = DQFValidator(config)

# DEBUG VALIDATOR
print("\n=== DEBUG VALIDATOR ===")
print(f"Total checks initialized: {len(validator.checks)}")
print(f"Enabled checks: {list(validator.enabled_checks.keys())}")
print(f"Expected: 3 checks (check_1_source, check_2_integrity, check_3_calendar)")

# Run validation
report = validator.validate(data, symbol="TEST", source="debug")

# DEBUG REPORT
print("\n=== DEBUG REPORT ===")
print(f"Total checks in report: {len(report.check_results)}")
print(f"Check results keys: {list(report.check_results.keys())}")
print(f"Expected: 3 results")

# ASSERTION
assert len(report.check_results) == 3, f"Expected 3 checks, got {len(report.check_results)}"
print("\n✅ TEST PASSED")
