"""
Debug script to diagnose config.checks structure issue.
"""

from dqf.core.config import DQFConfig

# Create config
config = DQFConfig()

print("\n=== INITIAL CONFIG STATE ===")
print(f"Type: {type(config.checks)}")
print(f"Keys: {list(config.checks.keys())}")
print(f"check_4_ffill initial: {config.checks.get('check_4_ffill')}")

# Modify like test does
print("\n=== MODIFYING CONFIG ===")
config.checks["check_1_source"]["enabled"] = True
config.checks["check_2_integrity"]["enabled"] = True
config.checks["check_3_calendar"]["enabled"] = True
config.checks["check_4_ffill"]["enabled"] = False
config.checks["check_5_trace"]["enabled"] = False
config.checks["check_6_sanity"]["enabled"] = False
config.checks["check_7_logging"]["enabled"] = False

print("\n=== AFTER MODIFICATION ===")
for check_id in ["check_1_source", "check_2_integrity", "check_3_calendar",
                 "check_4_ffill", "check_5_trace", "check_6_sanity", "check_7_logging"]:
    check_config = config.checks.get(check_id, {})
    enabled = check_config.get("enabled", "KEY_MISSING")
    print(f"{check_id}:")
    print(f"  Full config: {check_config}")
    print(f"  enabled value: {enabled}")
    print(f"  Type: {type(enabled)}")

# Test what validator sees
print("\n=== WHAT VALIDATOR SEES ===")
for check_id in config.checks.keys():
    check_config = config.checks.get(check_id, {})
    is_enabled = check_config.get("enabled", True)  # Same as validator.py line 73
    print(f"{check_id}: config={check_config} → is_enabled={is_enabled}")

# Expected behavior
print("\n=== EXPECTED vs ACTUAL ===")
expected_enabled = {"check_1_source", "check_2_integrity", "check_3_calendar"}
actual_enabled = {
    check_id for check_id in config.checks.keys()
    if config.checks.get(check_id, {}).get("enabled", True)
}
print(f"Expected enabled: {expected_enabled}")
print(f"Actual enabled: {actual_enabled}")
print(f"Match: {expected_enabled == actual_enabled}")

if expected_enabled != actual_enabled:
    print("\n❌ MISMATCH DETECTED")
    print(f"Extra enabled: {actual_enabled - expected_enabled}")
    print(f"Missing enabled: {expected_enabled - actual_enabled}")
else:
    print("\n✅ CONFIG STRUCTURE CORRECT")