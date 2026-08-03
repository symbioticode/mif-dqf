# DQF API Reference

**Version**: 1.1.0  
**Last Updated**: April 12, 2026  
**Status**: ✅ Production Ready (189/189 tests passing)  
**Python**: 3.10+

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Core Classes](#core-classes)
   - [DQFValidator](#dqfvalidator)
   - [DQFReport](#dqfreport)
   - [DQFConfig](#dqfconfig)
4. [The 7 Checks](#the-7-checks)
5. [Utils & Helpers](#utils--helpers)
6. [Configuration Schema](#configuration-schema)
7. [Examples & Best Practices](#examples--best-practices)

---

## Introduction

DQF (Data Quality Framework) is a production-ready validation framework for financial OHLCV (Open, High, Low, Close, Volume) data. It performs 7 comprehensive checks to ensure data integrity before analysis or trading.

### Design Philosophy

**"Without purification, no sacred act is valid. Without DQF, no analysis is trustworthy."**

Inspired by ritual purification practices (Islamic Wudu, Shinto Temizuya), DQF ensures data purity through systematic validation.

### Key Features

- ✅ **7 Comprehensive Checks**: Source, Integrity, Calendar, Forward-Fill, Index, Sanity, Logging
- ✅ **Production Ready**: 104/104 tests passing, 77% coverage
- ✅ **Reproducible**: Same data → Same results (always)
- ✅ **Transparent**: Full provenance tracking, complete audit trail
- ✅ **Extensible**: Add custom checks easily

---

## Quick Start

### Installation

```bash
pip install dqf
```

### Basic Usage

```python
import pandas as pd
from pathlib import Path
from dqf import DQFValidator, DQFConfig, DQFMode

# Load your data (timezone-aware index required)
data = pd.read_csv("spy.csv", index_col=0, parse_dates=True)
data.index = data.index.tz_localize("UTC")

# CERTIFICATION mode — strict, deterministic, calendar required
config    = DQFConfig(mode=DQFMode.CERTIFICATION)
validator = DQFValidator(config)
report    = validator.validate(data, calendar="NYSE")

if report.is_certified:
    print(f"✅ CERTIFIED  MPI={report.purity_index:.1f}/100  gate={report.precondition_gate}")
    print(f"   MIF-UID: {report.mif_uid}")
    clean_data = report.cleaned_data
else:
    print(f"❌ {report.overall_status}  (gate={report.precondition_gate})")
    print(f"   CORE:     {report.core_results}")
    print(f"   ADVISORY: {report.advisory_results}")

# Export MIF-Lite manifest (to_json / to_yaml return strings)
Path("validation_report.json").write_text(report.to_json())
Path("validation_report.yaml").write_text(report.to_yaml())

# Human-readable summary
report.print_summary()
```

---

## Core Classes

### DQFValidator

**Description**: Orchestrates all 7 data quality checks.

**Import**:
```python
from dqf import DQFValidator
```

---

#### Constructor

```python
DQFValidator(config: DQFConfig)
```

**Parameters**:
- `config` (DQFConfig): Configuration object with check parameters

**Example**:
```python
from dqf import DQFValidator, DQFConfig

config = DQFConfig()  # Default config
validator = DQFValidator(config)
```

---

#### validate()

```python
validate(
    df: pd.DataFrame,
    calendar: str | None = None,
    raw_data_hash: str | None = None,
    enable_cleaning_log: bool = False,
) -> DQFReport
```

**Description**: Run all enabled checks on DataFrame.

**Parameters**:
- `df` (pd.DataFrame): DataFrame with datetime index and OHLCV columns
  - Required columns: `open`, `high`, `low`, `close`, `volume`
  - Column names are case-insensitive
  - Index must be DatetimeIndex (timezone-aware recommended)
- `calendar` (str, optional): Declared trading calendar (e.g. "NYSE"). Required
  in CERTIFICATION mode; optional in DIAGNOSTIC.
- `raw_data_hash` (str, optional): SHA-256 of the raw input data (hex string,
  prefixed `"sha256:"`). Computed from `df` if not provided. Callers should
  provide this when they hold the original bytes (e.g. from a DAL handoff),
  so the hash reflects the source, not the in-memory copy.
- `enable_cleaning_log` (bool, optional): When True, aggregate per-row
  intervention entries from all checks and embed a Parquet cleaning log in
  the manifest (v1.2). Default False.

**Returns**:
- `DQFReport`: Report object with results and cleaned data

**Raises**:
- `TypeError`: If `df` is not a pandas DataFrame
  - Message format: `"df must be a pandas DataFrame, got {actual_type}"`

**Example**:
```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

# Load data with timezone
dates = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
data = pd.DataFrame({
    "open": [100 + i for i in range(100)],
    "high": [105 + i for i in range(100)],
    "low": [95 + i for i in range(100)],
    "close": [102 + i for i in range(100)],
    "volume": [1000000 + i*1000 for i in range(100)],
}, index=dates)

config = DQFConfig()
validator = DQFValidator(config)
report = validator.validate(data, calendar="NYSE")

print(f"Status: {report.overall_status}")
print(f"Checks: {report.checks_passed}/{report.total_checks}")
```

---

#### add_custom_check()

```python
add_custom_check(check_id: str, check: BaseCheck) -> None
```

**Description**: Add a custom check to the validation pipeline.

**Parameters**:
- `check_id` (str): Unique identifier for custom check (e.g., "check_8_custom")
- `check` (BaseCheck): Instance of custom check class

**Raises**:
- `ValueError`: If `check_id` already exists

**Example**:
```python
from dqf import DQFValidator, DQFConfig
from dqf.checks.base import BaseCheck, CheckResult

class VolumeSpikesCheck(BaseCheck):
    def __init__(self):
        super().__init__(
            check_id="check_8_volume_spikes",
            check_name="Volume Spikes Detection"
        )
    
    def run(self, df, **kwargs):
        vol_mean = df['volume'].mean()
        spikes = (df['volume'] > vol_mean * 5).sum()
        
        if spikes > 3:
            return self._create_result(
                status='FAIL',
                severity='WARNING',
                message=f'{spikes} volume spikes detected (>5× mean)',
                details={'spike_count': spikes, 'threshold': vol_mean * 5}
            )
        
        return self._create_result(
            status='PASS',
            message='No excessive volume spikes detected'
        )

# Usage
validator = DQFValidator(DQFConfig())
validator.add_custom_check('check_8_volume_spikes', VolumeSpikesCheck())
report = validator.validate(data)
```

---

### DQFReport

**Description**: Container for validation results.

**Import**:
```python
from dqf import DQFReport
```

---

#### Properties (v1.1)

All properties are read-only accessors on the underlying MIF-Lite manifest dict.

```python
# Status
overall_status: str     # 'CERTIFIED', 'WARNING', or 'VOID'
is_certified: bool      # True only when overall_status == 'CERTIFIED'
purity_index: float     # MIF Purity Index — [0.0, 100.0]. 100.0 = zero intervention
precondition_gate: float  # 1.0 (CERTIFIED) | 0.8 (WARNING, MPI-capped) | 0.0 (VOID)

# Identity
mif_uid: str            # 'sha256:<hex>' — deterministic, reproducible
dqf_version: str        # e.g. '1.1.0'
mode: str               # 'CERTIFICATION' or 'DIAGNOSTIC'
calendar: str           # Declared calendar or 'UNKNOWN'

# Check results
core_results: dict      # {'C2': 'PASS', 'C3': 'PASS', 'C5': 'PASS', 'PROD': 'PASS'}
advisory_results: dict  # {'C1': 'SKIP', 'C4': 'PASS'}

# Vitality signal (D-SIG v0.5)
vitality_score: int     # Integer in [0, 100]
vitality_label: str     # 'EXCELLENT' | 'GOOD' | 'DEGRADED' | 'CRITICAL'

# Data
cleaned_data: pd.DataFrame  # Validated DataFrame (passthrough in Phase 1)

# Raw manifest
manifest: dict          # Full MIF-Lite dict — single source of truth
```

**Example**:
```python
report = validator.validate(data, calendar="NYSE")

print(f"Status  : {report.overall_status}")          # 'CERTIFIED'
print(f"MPI     : {report.purity_index:.1f}/100")    # '100.0/100'
print(f"Gate    : {report.precondition_gate}")        # '1.0'
print(f"UID     : {report.mif_uid[:48]}...")
print(f"Vitality: {report.vitality_label}")           # 'EXCELLENT'
print(f"CORE    : {report.core_results}")
print(f"ADVISORY: {report.advisory_results}")

# Use certified data downstream
if report.is_certified:
    run_backtest(report.cleaned_data)
```

> **Removed in v1.1** (were in v1.0): `checks_passed`, `total_checks`, `check_results`,
> `all_issues`, `timestamp`, `provenance` (replaced by `manifest["provenance"]`).

---

#### to_yaml()

```python
to_yaml() -> str
```

**Description**: Return the MIF-Lite manifest as a YAML string.

> **Breaking change from v1.0**: No longer writes to a file. Returns a `str`.
> Use `pathlib.Path("report.yaml").write_text(report.to_yaml())` to persist.

**Example**:
```python
from pathlib import Path

report = validator.validate(data, calendar="NYSE")
Path("report.yaml").write_text(report.to_yaml())
```

**Output Format** (MIF-Lite manifest):
```yaml
'@context': https://mif.dev/v1
'@type': DataCertification
mif_uid: sha256:a3f9...
status:
  overall: CERTIFIED
  purity_index: 100.0
  precondition_gate: 1.0
checks:
  core:
    C2: PASS
    C3: PASS
    C5: PASS
    PROD: PASS
  advisory:
    C1: SKIP
    C4: PASS
vitality_signal:
  score: 100
  label: EXCELLENT
  trend: STABLE
provenance:
  dqf_version: 1.1.0
  mode: CERTIFICATION
  source_hash: sha256:...
  calendar: NYSE
  cleaning_log_uri: null
signature:
  type: sha256_provisional
  value: ...
```

---

#### to_json()

```python
to_json(indent: int = 2) -> str
```

**Description**: Return the MIF-Lite manifest as a JSON string.

> **Breaking change from v1.0**: No longer writes to a file. Returns a `str`.
> Use `pathlib.Path("report.json").write_text(report.to_json())` to persist.

**Parameters**:
- `indent` (int, optional): JSON indentation (default: 2)

**Example**:
```python
from pathlib import Path

report = validator.validate(data, calendar="NYSE")
Path("report.json").write_text(report.to_json())
```

---

#### to_dict()

```python
to_dict() -> Dict
```

**Description**: Convert report to Python dictionary (JSON-serializable).

**Returns**:
- `Dict`: Report as dictionary

**Example**:
```python
report = validator.validate(data)
report_dict = report.to_dict()

# Use in API response
import json
json_response = json.dumps(report_dict, indent=2)
```

---

#### print_summary()

```python
print_summary() -> None
```

**Description**: Print human-readable summary to console.

**Example**:
```python
report = validator.validate(data)
report.print_summary()
```

**Output**:
```
============================================================
DQF VALIDATION REPORT
============================================================

Overall Status: PASS
Checks Passed:  7/7
Issues Found:   0
Timestamp:      2026-01-20 14:30:00 UTC

------------------------------------------------------------
INDIVIDUAL CHECK RESULTS
------------------------------------------------------------
✅ Source Uniqueness: PASS
   Message: Source uniqueness validated successfully

✅ OHLCV Integrity: PASS
   Message: OHLCV integrity validated successfully

✅ Calendar Alignment: PASS
   Message: Calendar alignment validated successfully

✅ Forward Fill Detection: PASS
   Message: No excessive forward-fill detected

✅ Index Traceability: PASS
   Message: Index traceability validated successfully

✅ Sanity Tests: PASS
   Message: All sanity checks passed

✅ Comprehensive Logging: PASS
   Message: Comprehensive logging completed successfully

------------------------------------------------------------
✅ No issues detected - data is clean!
------------------------------------------------------------
```

---

### DQFConfig

**Description**: Configuration dataclass for DQF v1.1 validation.

**Import**:
```python
from dqf import DQFConfig, DQFMode
```

---

#### Constructor

```python
DQFConfig(
    mode: DQFMode,                    # REQUIRED — no default
    c4_max_consecutive_ffill: int = 3,
    c4_warn_threshold: int = 2,
    c1_enabled: bool = False,         # DAL-pending (Phase 2+)
)
```

**Parameters**:
- `mode` (**required**): `DQFMode.CERTIFICATION` or `DQFMode.DIAGNOSTIC`. Raises `TypeError` if absent or wrong type.
- `c4_max_consecutive_ffill`: Maximum consecutive identical values before C4 FAILS (default: 3).
- `c4_warn_threshold`: Consecutive repeats before C4 WARNS (default: 2). Must be < `c4_max_consecutive_ffill`.
- `c1_enabled`: Set `True` when DAL is connected (Phase 2+). Default `False` → C1 = SKIP.

**Raises**:
- `TypeError`: If `mode` is missing or not a `DQFMode` instance.
- `ValueError`: If `c4_warn_threshold >= c4_max_consecutive_ffill`.

**Example**:
```python
from dqf import DQFConfig, DQFMode

# CERTIFICATION mode (strict — for production pipelines)
config = DQFConfig(mode=DQFMode.CERTIFICATION)

# DIAGNOSTIC mode (lenient — for exploration / CI)
config = DQFConfig(mode=DQFMode.DIAGNOSTIC)

# Custom ffill thresholds
config = DQFConfig(
    mode=DQFMode.CERTIFICATION,
    c4_warn_threshold=1,
    c4_max_consecutive_ffill=2,
)
```

---

#### from_yaml()

```python
@classmethod
from_yaml(cls, filepath: str) -> DQFConfig
```

**Description**: Load configuration from YAML file.

**Parameters**:
- `filepath` (str): Path to YAML config file

**Returns**:
- `DQFConfig`: Configuration object

**Raises**:
- `FileNotFoundError`: If config file doesn't exist
- `yaml.YAMLError`: If YAML is malformed

**Example**:
```yaml
# config.yaml (v1.1)
mode: CERTIFICATION
c4_max_consecutive_ffill: 3
c4_warn_threshold: 2
```

```python
from dqf import DQFConfig, DQFValidator

config = DQFConfig.from_yaml("config.yaml")
validator = DQFValidator(config)
```

---

#### from_dict()

```python
@classmethod
from_dict(cls, config_dict: Dict) -> DQFConfig
```

**Description**: Create config from dictionary.

**Parameters**:
- `config_dict` (Dict): Configuration as dictionary

**Returns**:
- `DQFConfig`: Configuration object

**Example**:
```python
config_dict = {
    "mode": "CERTIFICATION",
    "c4_max_consecutive_ffill": 3,
    "c4_warn_threshold": 2,
}

config = DQFConfig.from_dict(config_dict)
```

---

#### validate()

```python
validate() -> bool
```

**Description**: Validate configuration parameters.

**Returns**:
- `bool`: True if valid

**Raises**:
- `ValueError`: If invalid configuration detected

**Example**:
```python
config = DQFConfig(
    check_2_integrity={'max_violation_rate': -0.5}  # Invalid
)

try:
    config.validate()
except ValueError as e:
    print(f"Invalid config: {e}")
    # Output: "Invalid config: max_violation_rate must be between 0 and 1"
```

---

## BaseCheck (Abstract Base Class)

**Description**: Base class for all checks (standard and custom).

**Import**:
```python
from dqf.checks.base import BaseCheck, CheckResult
```

---

#### Constructor

```python
BaseCheck(check_id: str, check_name: str)
```

**Parameters**:
- `check_id` (str): Unique identifier (e.g., "check_1_source")
- `check_name` (str): Human-readable name (e.g., "Source Uniqueness")

---

#### run() [Abstract]

```python
@abstractmethod
def run(self, df: pd.DataFrame, **kwargs) -> CheckResult:
    """
    Execute check on DataFrame.
    
    Args:
        df: DataFrame to validate
        **kwargs: Additional parameters
    
    Returns:
        CheckResult with status and details
    """
    pass
```

---

#### _create_result() [Helper]

```python
def _create_result(
    self,
    status: str,
    message: str = "",
    severity: str = "INFO",
    details: Dict = None
) -> CheckResult:
    """
    Helper to create CheckResult.
    
    Args:
        status: 'PASS' or 'FAIL'
        message: Human-readable message
        severity: 'INFO', 'WARNING', or 'CRITICAL'
        details: Optional additional details
    
    Returns:
        CheckResult instance
    """
```

**Example**:
```python
return self._create_result(
    status='PASS',
    message='Check passed successfully',
    severity='INFO',
    details={'rows_checked': 100}
)
```

---

#### _validate_dataframe() [Helper]

```python
def _validate_dataframe(self, df: pd.DataFrame) -> None:
    """
    Validate that input is a proper DataFrame.
    
    Args:
        df: Object to validate
    
    Raises:
        TypeError: If df is not a pandas DataFrame
            Message format: "Expected pd.DataFrame, got {actual_type}"
            Note: Exact wording may vary slightly for clarity
        ValueError: If DataFrame is empty
    
    Example:
        >>> self._validate_dataframe([1, 2, 3])
        TypeError: Expected pd.DataFrame, got list
        
        >>> self._validate_dataframe(pd.DataFrame())
        ValueError: DataFrame is empty
    """
```

---

## CheckResult (Data Class)

**Description**: Result of a single check.

**Import**:
```python
from dqf.checks.base import CheckResult
```

**Attributes**:
```python
check_name: str              # Check identifier
status: str                  # 'PASS' or 'FAIL'
severity: str                # 'INFO', 'WARNING', 'CRITICAL'
message: str                 # Human-readable message
details: Dict                # Additional details (optional)
```

**Example**:
```python
result = CheckResult(
    check_name='check_2_integrity',
    status='FAIL',
    severity='CRITICAL',
    message='3 OHLCV integrity violations detected',
    details={
        'high_low_violations': 3,
        'violation_indices': [42, 87, 153]
    }
)

# Convert to dict
result_dict = result.to_dict()
```

---

**End of Part 1: Core Classes**

**Lines**: ~880
**Next Part**: The 7 Checks (Check 1-4)


# DQF API Reference v1.0.0 - Part 2: The 7 Checks

## The 7 Checks

### Overview

DQF performs 7 comprehensive checks to ensure data quality:

| Check | Name | Purpose | Severity |
|-------|------|---------|----------|
| 1 | Source Uniqueness | Single canonical source + metadata | INFO/WARNING |
| 2 | OHLCV Integrity | Market physics laws (H≥L, etc.) | CRITICAL |
| 3 | Calendar Alignment | Trading calendar validation | WARNING |
| 4 | Forward-Fill Detection | Interpolation abuse detection | WARNING/CRITICAL |
| 5 | Index Traceability | Unique, chronological, timezone | CRITICAL |
| 6 | Sanity Tests | Statistical anomalies | WARNING |
| 7 | Comprehensive Logging | Provenance tracking | INFO |

---

## Check 1: Source Uniqueness

**Purpose**: Validate data comes from single canonical source with proper metadata.

**Import**:
```python
from dqf.checks.check_1_source import SourceUniquenessCheck
```

---

### Parameters

```yaml
check_1_source:
  enabled: true
  require_metadata: false      # Require source metadata
  max_gap_days: 30            # Max allowed gap between data points
```

**Default Values**:
- `enabled`: `true`
- `require_metadata`: `false`
- `max_gap_days`: `30`

---

### Validation Rules

1. **Source Validation**:
   - If `source` provided via kwargs: validates it's non-empty
   - If `require_metadata=true`: fails if no source provided

2. **Gap Detection**:
   - Calculates gaps between consecutive data points
   - Warns if gap exceeds `max_gap_days`
   - Note: Gaps may be legitimate (weekends, holidays)

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_1_source',
    status='PASS' | 'FAIL' | 'WARNING',
    severity='INFO' | 'WARNING',
    message='Source validation details',
    details={
        'source': 'yahoo_finance',      # Source identifier (if provided)
        'has_metadata': True,            # Whether metadata present
        'max_gap_detected': 2,           # Max gap in days
        'gap_threshold': 30,             # Configured threshold
        'gaps_over_threshold': 0         # Number of gaps exceeding threshold
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_1_source import SourceUniquenessCheck
import pandas as pd

# Create check with custom parameters
check = SourceUniquenessCheck(
    require_metadata=True,
    max_gap_days=7
)

# Run check
result = check.run(
    data,
    source='yahoo_finance',  # Provide source as kwarg
    symbol='BTC-USD'
)

print(f"Status: {result.status}")
print(f"Source: {result.details['source']}")
print(f"Max Gap: {result.details['max_gap_detected']} days")
```

---

### Pass/Fail Criteria

**PASS**:
- Source provided (if `require_metadata=true`)
- All gaps ≤ `max_gap_days`

**WARNING**:
- Gaps detected > `max_gap_days` (data may have legitimate gaps)
- Source not provided but `require_metadata=false`

**FAIL**:
- Source required (`require_metadata=true`) but not provided
- Source is empty string

---

## Check 2: OHLCV Integrity

**Purpose**: Enforce market physics laws (H≥L, H≥O/C, V≥0, no NaN).

**Import**:
```python
from dqf.checks.check_2_integrity import OHLCVIntegrityCheck
```

---

### Parameters

```yaml
check_2_integrity:
  enabled: true
  max_violation_rate: 0.01    # 1% violations tolerated
  required_columns:
    - open
    - high
    - low
    - close
    - volume
```

**Default Values**:
- `enabled`: `true`
- `max_violation_rate`: `0.01` (1%)
- `required_columns`: `['open', 'high', 'low', 'close', 'volume']`

---

### Validation Rules

1. **Missing Columns**: Fails if any required column missing
2. **High ≥ Low**: CRITICAL violation if violated
3. **Close ∈ [Low, High]**: CRITICAL if close outside range
4. **Open ∈ [Low, High]**: WARNING if open outside range
5. **Volume ≥ 0**: CRITICAL if negative volume
6. **No NaN in OHLC**: CRITICAL if NaN found
7. **NaN in Volume**: Acceptable (some sources don't track volume)

**Violation Counting**:
- Counts **per violation**, not per row
- Example: 1 row with H<L + C>H = 2 violations

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_2_integrity',
    status='PASS' | 'FAIL',
    severity='INFO' | 'CRITICAL',
    message='X violations detected',
    details={
        'total_rows': 100,
        'total_violations': 3,
        'violation_rate': 0.03,          # 3%
        'max_violation_rate': 0.01,      # Threshold
        'violation_breakdown': {
            'high_low_violations': 1,
            'close_range_violations': 2,
            'open_range_violations': 0,
            'negative_volume': 0,
            'nan_ohlc': 0,
            'nan_volume': 0
        }
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_2_integrity import OHLCVIntegrityCheck

# Create check with strict threshold
check = OHLCVIntegrityCheck(max_violation_rate=0.005)  # 0.5%

# Run check
result = check.run(data)

if result.status == 'FAIL':
    violations = result.details['violation_breakdown']
    print(f"High<Low violations: {violations['high_low_violations']}")
    print(f"Close out of range: {violations['close_range_violations']}")
```

---

### Pass/Fail Criteria

**PASS**:
- All required columns present
- Violation rate ≤ `max_violation_rate`

**FAIL**:
- Missing required columns
- Violation rate > `max_violation_rate`
- Any CRITICAL violation (H<L, C∉[L,H], V<0, NaN in OHLC)

---

### Common Issues

**Issue**: False positives due to data precision
```python
# Float precision can cause false H<L
high = 50.00000001
low = 50.0

# Solution: Use tolerance in comparison (already implemented internally)
```

**Issue**: Volume = 0 vs NaN
```python
# Volume = 0: Legitimate (holidays, after-hours)
# Volume = NaN: Acceptable (some sources don't track)
# Volume < 0: CRITICAL violation
```

---

## Check 3: Calendar Alignment

**Purpose**: Detect trading calendar and validate only trading days present.

**Import**:
```python
from dqf.checks.check_3_calendar import CalendarAlignmentCheck
```

---

### Parameters

```yaml
check_3_calendar:
  enabled: true
  auto_detect: true           # Auto-detect NYSE/CRYPTO/FOREX
  calendar: null              # Override: 'NYSE', 'CRYPTO', 'FOREX'
  strict_mode: false          # If true, fail on holidays
```

**Default Values**:
- `enabled`: `true`
- `auto_detect`: `true`
- `calendar`: `null` (auto-detect)
- `strict_mode`: `false`

---

### Calendar Detection Logic

**Auto-Detection Sequence**:
1. Check for weekends (Saturday/Sunday):
   - If present → **CRYPTO** (24/7 trading)
2. Check for Friday-Sunday gap:
   - If gap detected → **FOREX** (24/5 trading, closed weekends)
3. Default → **NYSE** (weekdays only, major holidays excluded)

**Supported Calendars**:
- `NYSE`: US stock market (weekdays, major holidays excluded)
- `CRYPTO`: 24/7 trading (all days valid)
- `FOREX`: 24/5 trading (closed weekends)

---

### Validation Rules

**NYSE Calendar**:
- Weekdays only (Monday-Friday)
- Excludes major US holidays:
  - New Year's Day
  - MLK Day
  - Presidents' Day
  - Good Friday
  - Memorial Day
  - Independence Day
  - Labor Day
  - Thanksgiving
  - Christmas

**CRYPTO Calendar**:
- All days valid (24/7)
- No holidays

**FOREX Calendar**:
- Monday 00:00 - Friday 23:59 (UTC)
- Closed weekends

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_3_calendar',
    status='PASS' | 'WARNING',
    severity='INFO' | 'WARNING',
    message='Calendar validation details',
    details={
        'detected_calendar': 'NYSE',     # Auto-detected or specified
        'weekends_detected': 0,          # Number of weekend days
        'holidays_detected': 2,          # Number of holidays
        'total_trading_days': 187,       # Total days in dataset
        'expected_trading_days': 252,    # Expected for date range
        'missing_days': 65               # Expected - Actual
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_3_calendar import CalendarAlignmentCheck

# Auto-detect calendar
check = CalendarAlignmentCheck(auto_detect=True)
result = check.run(data)
print(f"Detected: {result.details['detected_calendar']}")

# Force specific calendar
check = CalendarAlignmentCheck(calendar='NYSE', strict_mode=True)
result = check.run(data)

# Override detection
check = CalendarAlignmentCheck(calendar='CRYPTO')
result = check.run(btc_data)  # Will validate as 24/7
```

---

### Pass/Fail Criteria

**PASS**:
- Calendar detected successfully
- No weekends (NYSE/FOREX) or all days valid (CRYPTO)
- Holidays acceptable if `strict_mode=false`

**WARNING**:
- Weekends detected in NYSE/FOREX data
- Holidays detected if `strict_mode=false`
- Missing expected trading days

**FAIL** (only if `strict_mode=true`):
- Holidays present in NYSE/FOREX data

---

### Common Issues

**Issue**: False weekend detection in CRYPTO
```python
# Bitcoin trades 24/7, but data may have gaps
# Solution: Calendar auto-detects CRYPTO if weekends present
```

**Issue**: Holiday handling
```python
# NYSE closed Dec 25, but data may include it
# Solution: strict_mode=false (default) treats as WARNING
```

---

## Check 4: Forward-Fill Detection

**Purpose**: Detect excessive forward-filling (data interpolation abuse).

**Import**:
```python
from dqf.checks.check_4_ffill import ForwardFillLimitsCheck
```

---

### Parameters

```yaml
check_4_ffill:
  enabled: true
  max_consecutive: 3          # Max consecutive forward-filled days
  severity: 'WARNING'         # 'WARNING' or 'CRITICAL'
  columns_to_check:           # Columns to check for ffill
    - open
    - high
    - low
    - close
```

**Default Values**:
- `enabled`: `true`
- `max_consecutive`: `3`
- `severity`: `'WARNING'`
- `columns_to_check`: `['open', 'high', 'low', 'close']`

---

### Detection Logic

**Forward-Fill Sequence**:
- Identifies consecutive rows where OHLC values are **identical**
- Excludes NaN sequences (not forward-fill, just missing data)
- Reports longest sequence found

**Example**:
```
Date        | Open  | High  | Low   | Close
------------|-------|-------|-------|-------
2024-01-01  | 100.0 | 105.0 | 95.0  | 102.0  ← Original
2024-01-02  | 100.0 | 105.0 | 95.0  | 102.0  ← Ffill 1
2024-01-03  | 100.0 | 105.0 | 95.0  | 102.0  ← Ffill 2
2024-01-04  | 100.0 | 105.0 | 95.0  | 102.0  ← Ffill 3 (WARNING if max=3)
2024-01-05  | 101.0 | 106.0 | 96.0  | 103.0  ← New data
```

**Not Detected as Forward-Fill**:
- NaN sequences (missing data)
- Volume = 0 (legitimate, e.g., holidays)
- Single repeated value (could be legitimate flat price)

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_4_ffill',
    status='PASS' | 'FAIL',
    severity='WARNING' | 'CRITICAL',
    message='X consecutive forward-filled days detected',
    details={
        'max_consecutive_ffill': 2,      # Longest sequence found
        'threshold': 3,                  # Configured max
        'sequences_detected': 5,         # Total sequences found
        'ffill_sequences': [             # Details of sequences
            {
                'start_index': 10,
                'end_index': 12,
                'length': 3,
                'columns': ['open', 'high', 'low', 'close']
            }
        ]
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_4_ffill import ForwardFillLimitsCheck

# Strict: No forward-fill allowed (CRITICAL severity)
check = ForwardFillLimitsCheck(
    max_consecutive=1,
    severity='CRITICAL'  # Treat as critical error
)
result = check.run(data)

# Lenient: Allow some forward-fill (WARNING severity)
check_lenient = ForwardFillLimitsCheck(
    max_consecutive=3,
    severity='WARNING'  # Just a warning
)
result_lenient = check_lenient.run(data)

if result.status == 'FAIL':
    sequences = result.details['ffill_sequences']
    for seq in sequences:
        print(f"Ffill detected: rows {seq['start_index']}-{seq['end_index']}")
```

---

### Pass/Fail Criteria

**PASS**:
- No forward-fill sequences detected
- All sequences ≤ `max_consecutive`

**FAIL** (if severity='WARNING'):
- Sequences detected > `max_consecutive`
- Status = 'WARNING' (data quality concern, not critical)

**FAIL** (if severity='CRITICAL'):
- Sequences detected > `max_consecutive`
- Status = 'FAIL' (critical data quality issue)

---

### Common Issues

**Issue**: Legitimate flat prices detected as ffill
```python
# Stock price can be legitimately flat for days
# Solution: Increase max_consecutive or check volume
```

**Issue**: NaN vs Forward-Fill
```python
# NaN: Missing data (not ffill)
# Identical OHLC: Potential ffill
# Solution: Check excludes NaN sequences automatically
```

**Issue**: Volume = 0 confused with ffill
```python
# Volume = 0: Legitimate (holidays, after-hours)
# Volume + OHLC identical: Potential ffill
# Solution: Check focuses on OHLC, not volume
```

---

**End of Part 2: Checks 1-4**

**Lines**: ~880
**Next Part**: Checks 5-7 + Utils & Helpers

# DQF API Reference v1.0.0 - Part 3: Checks 5-7 + Utils

## Check 5: Index Traceability

**Purpose**: Validate index is unique, chronological, and timezone-aware.

**Import**:
```python
from dqf.checks.check_5_trace import IndexTraceabilityCheck
```

---

### Parameters

```yaml
check_5_trace:
  enabled: true
  require_timezone: true      # Require timezone-aware index
  require_sorted: true        # Require chronological order
```

**Default Values**:
- `enabled`: `true`
- `require_timezone`: `true`
- `require_sorted`: `true`

---

### Validation Rules

1. **DatetimeIndex Type**: Index must be `pd.DatetimeIndex`
2. **No Duplicates**: No duplicate timestamps
3. **Chronological Order**: Timestamps sorted ascending
4. **Timezone Aware**: Index has timezone info (if `require_timezone=true`)

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_5_trace',
    status='PASS' | 'FAIL',
    severity='INFO' | 'CRITICAL',
    message='Index validation details',
    details={
        'is_datetime_index': True,       # Is DatetimeIndex
        'has_duplicates': False,         # Duplicate timestamps
        'is_sorted': True,               # Chronological order
        'has_timezone': True,            # Timezone aware
        'timezone': 'UTC',               # Timezone name
        'total_rows': 100,
        'duplicate_count': 0             # Number of duplicates
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_5_trace import IndexTraceabilityCheck

# Require timezone-aware index
check = IndexTraceabilityCheck(require_timezone=True)
result = check.run(data)

if result.status == 'FAIL':
    if not result.details['has_timezone']:
        print("⚠️ Index is not timezone-aware")
        # Fix: data.index = data.index.tz_localize('UTC')
    
    if result.details['has_duplicates']:
        print(f"⚠️ {result.details['duplicate_count']} duplicate timestamps")
        # Fix: data = data[~data.index.duplicated(keep='first')]
```

---

### Pass/Fail Criteria

**PASS**:
- Index is DatetimeIndex
- No duplicates
- Chronologically sorted
- Timezone-aware (if `require_timezone=true`)

**FAIL**:
- Not a DatetimeIndex
- Duplicates present
- Not sorted chronologically
- Not timezone-aware (if required)

---

### Common Issues

**Issue**: Missing timezone
```python
# Data without timezone
dates = pd.date_range("2024-01-01", periods=100)  # No tz
data = pd.DataFrame({...}, index=dates)

# Fix: Add timezone
data.index = data.index.tz_localize('UTC')
```

**Issue**: Duplicate timestamps
```python
# Data with duplicates (e.g., from merging sources)
data[data.index.duplicated()]

# Fix: Keep first occurrence
data = data[~data.index.duplicated(keep='first')]
```

**Issue**: Unsorted index
```python
# Data unsorted (e.g., from multiple sources)
data.sort_index(inplace=True)
```

---

## ~~Check 6: Sanity Tests~~ — REMOVED in v1.1

> **REMOVED in DQF v1.1.** Statistical sanity tests have been migrated to MIF Layer 1.
> The `SanityTestsCheck` class and `check_6_sanity.py` no longer exist.
> This section is kept for historical reference only. Do **not** use in new code.

---

**Purpose (v1.0 legacy)**: Detect statistical anomalies (extreme returns, zero volume, volatility spikes).

**Import**:
```python
from dqf.checks.check_6_sanity import SanityTestsCheck
```

---

### Parameters

```yaml
check_6_sanity:
  enabled: true
  max_return_threshold: 0.20        # 20% max daily return
  min_volume_days: 5                # Min days with volume > 0
  max_volatility_spike: 5.0         # Max Nx volatility spike
  zero_volume_threshold: 5          # Max consecutive zero volume days
```

**Default Values**:
- `enabled`: `true`
- `max_return_threshold`: `0.20` (20%)
- `min_volume_days`: `5`
- `max_volatility_spike`: `5.0` (5×)
- `zero_volume_threshold`: `5`

---

### Anomalies Detected

**1. Extreme Returns**:
- Daily return > `max_return_threshold`
- Calculation: `(close_t - close_t-1) / close_t-1`
- Example: 25% daily return (threshold 20%)

**2. Zero Volume Sequences**:
- Consecutive days with volume = 0
- Exceeds `zero_volume_threshold`
- Note: Volume = 0 can be legitimate (holidays)

**3. Volatility Spikes**:
- Return volatility > N× rolling average
- N = `max_volatility_spike`
- Calculation: `std(returns_window) > N × rolling_avg_std`

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_6_sanity',
    status='PASS' | 'WARNING',
    severity='WARNING',  # Always WARNING (statistical, not physical)
    message='X anomalies detected',
    details={
        'extreme_returns': 2,            # Count of extreme returns
        'extreme_return_dates': [        # Dates with extreme returns
            '2024-01-15',
            '2024-02-20'
        ],
        'zero_volume_sequences': 1,      # Count of sequences
        'max_zero_volume_length': 3,     # Longest sequence
        'volatility_spikes': 0,          # Count of spikes
        'total_anomalies': 3,            # Total anomalies
        'anomaly_rate': 0.03             # 3% of data
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_6_sanity import SanityTestsCheck

# Strict sanity checks
check = SanityTestsCheck(
    max_return_threshold=0.15,  # 15% max return
    zero_volume_threshold=3     # Max 3 days zero volume
)
result = check.run(data)

if result.details['extreme_returns'] > 0:
    dates = result.details['extreme_return_dates']
    print(f"⚠️ Extreme returns on: {', '.join(dates)}")
```

---

### Pass/Fail Criteria

**PASS**:
- No anomalies detected
- All statistical checks passed

**WARNING**:
- Anomalies detected (not critical, but worth investigating)
- Severity always 'WARNING' (statistical heuristic)

**Never FAIL**:
- This check never returns 'FAIL'
- Statistical anomalies are warnings, not errors

---

### Common Issues

**Issue**: False positives on volatile assets
```python
# Crypto can have legitimate 20%+ daily swings
# Solution: Increase max_return_threshold for volatile assets
check = SanityTestsCheck(max_return_threshold=0.30)  # 30% for crypto
```

**Issue**: Zero volume on holidays
```python
# Stock exchanges closed = volume = 0 (legitimate)
# Solution: Use Calendar Alignment check to exclude holidays first
```

**Issue**: Flash crash detection
```python
# Extreme return + volatility spike = potential flash crash
if result.details['extreme_returns'] > 0 and result.details['volatility_spikes'] > 0:
    print("⚠️ Potential flash crash detected")
```

---

## ~~Check 7: Comprehensive Logging~~ — REMOVED in v1.1

> **REMOVED in DQF v1.1.** Provenance tracking is now handled by the **PROD Envelope**,
> which produces a MIF-Lite manifest (`.mif.json`) with cryptographic signature.
> The `ComprehensiveLoggingCheck` class and `check_7_logging.py` no longer exist.
> This section is kept for historical reference only. Do **not** use in new code.

---

**Purpose (v1.0 legacy)**: Track complete provenance chain and export as JSON.

**Import**:
```python
from dqf.checks.check_7_logging import ComprehensiveLoggingCheck
```

---

### Parameters

```yaml
check_7_logging:
  enabled: true
  provenance_dir: 'provenance'      # Output directory
  export_format: 'json'             # Only JSON supported
```

**Default Values**:
- `enabled`: `true`
- `provenance_dir`: `'provenance'`
- `export_format`: `'json'`

---

### Provenance Structure

```json
{
  "source": "yahoo_finance",
  "symbol": "BTC-USD",
  "timestamp": "2026-01-20T14:30:00.123456+00:00",
  "dqf_version": "1.0.0",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "total_days": 187
  },
  "checks_run": [
    "check_1_source",
    "check_2_integrity",
    "check_3_calendar",
    "check_4_ffill",
    "check_5_trace",
    "check_6_sanity",
    "check_7_logging"
  ],
  "checksums": {
    "close": "a3f2b1c4e5d6f7a8b9c0d1e2f3a4b5c6",
    "volume": "d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"
  },
  "statistics": {
    "mean_close": 45234.56,
    "std_close": 3421.78,
    "min_close": 38000.12,
    "max_close": 52000.89,
    "total_volume": 1234567890
  },
  "transformations": []
}
```

---

### CheckResult Structure

```python
CheckResult(
    check_name='check_7_logging',
    status='PASS',
    severity='INFO',
    message='Comprehensive logging completed successfully',
    details={
        'provenance_file': 'provenance/BTC-USD_20260120.json',
        'checksum_close': 'a3f2b1c4e5...',
        'checksum_volume': 'd5e6f7a8b9...',
        'total_rows': 187
    }
)
```

---

### Example Usage

```python
from dqf.checks.check_7_logging import ComprehensiveLoggingCheck

# Custom provenance directory
check = ComprehensiveLoggingCheck(
    provenance_dir='custom_provenance'
)
result = check.run(data, symbol='BTC-USD', source='yahoo')

print(f"Provenance saved: {result.details['provenance_file']}")
```

---

### Provenance Verification

```python
from dqf.utils.provenance import ProvenanceTracker

# Verify data hasn't changed
is_valid = ProvenanceTracker.verify_provenance(
    'provenance/BTC-USD_20260120.json',
    current_data
)

if is_valid:
    print("✅ Data unchanged since validation")
else:
    print("❌ Data has been modified")
```

---

## Utils & Helpers

### calendar.py

#### detect_trading_calendar()

```python
detect_trading_calendar(df: pd.DataFrame) -> str
```

**Description**: Auto-detect trading calendar based on data patterns.

**Algorithm**:
1. Check for weekends (Sat/Sun) → CRYPTO
2. Check for Friday-Sunday gaps → FOREX
3. Default → NYSE

**Returns**:
- `'CRYPTO'`: 24/7 trading (weekends present)
- `'FOREX'`: 24/5 trading (Friday-Sunday gaps)
- `'NYSE'`: Weekdays only

**Example**:
```python
from dqf.utils.calendar import detect_trading_calendar

calendar = detect_trading_calendar(btc_data)
print(f"Detected: {calendar}")  # Output: CRYPTO
```

---

#### is_trading_day()

```python
is_trading_day(date: pd.Timestamp, calendar: str = 'NYSE') -> bool
```

**Description**: Check if given date is a trading day.

**Parameters**:
- `date` (pd.Timestamp): Date to check
- `calendar` (str): 'NYSE', 'CRYPTO', or 'FOREX'

**Returns**:
- `bool`: True if trading day

**Example**:
```python
from dqf.utils.calendar import is_trading_day
import pandas as pd

date = pd.Timestamp('2024-12-25')  # Christmas
is_open = is_trading_day(date, calendar='NYSE')
print(is_open)  # False

# CRYPTO always open
is_open_crypto = is_trading_day(date, calendar='CRYPTO')
print(is_open_crypto)  # True
```

---

#### get_trading_days()

```python
get_trading_days(
    start: pd.Timestamp,
    end: pd.Timestamp,
    calendar: str = 'NYSE'
) -> pd.DatetimeIndex
```

**Description**: Get all trading days in date range.

**Example**:
```python
from dqf.utils.calendar import get_trading_days
import pandas as pd

start = pd.Timestamp('2024-01-01')
end = pd.Timestamp('2024-12-31')
trading_days = get_trading_days(start, end, calendar='NYSE')

print(f"Trading days: {len(trading_days)}")  # ~252 days
```

---

### provenance.py

#### ProvenanceTracker

```python
ProvenanceTracker(output_dir: str = 'provenance')
```

**Description**: Tracks data provenance and exports to JSON.

---

##### save_provenance()

```python
save_provenance(
    symbol: str,
    df: pd.DataFrame,
    source: str = None,
    metadata: Dict = None
) -> str
```

**Parameters**:
- `symbol` (str): Ticker symbol
- `df` (pd.DataFrame): DataFrame to track
- `source` (str, optional): Data source
- `metadata` (Dict, optional): Additional metadata

**Returns**:
- `str`: Path to saved provenance file

**Example**:
```python
from dqf.utils.provenance import ProvenanceTracker

tracker = ProvenanceTracker(output_dir='custom_provenance')
filepath = tracker.save_provenance(
    symbol='BTC-USD',
    df=data,
    source='yahoo',
    metadata={'download_date': '2026-01-20'}
)
print(f"Saved: {filepath}")
```

---

##### verify_provenance()

```python
@staticmethod
verify_provenance(
    provenance_file: str,
    current_df: pd.DataFrame
) -> bool
```

**Description**: Verify DataFrame matches saved provenance.

**Parameters**:
- `provenance_file` (str): Path to provenance JSON
- `current_df` (pd.DataFrame): DataFrame to verify

**Returns**:
- `bool`: True if checksums match

**Example**:
```python
from dqf.utils.provenance import ProvenanceTracker

is_valid = ProvenanceTracker.verify_provenance(
    'provenance/BTC-USD_20260120.json',
    current_data
)

if not is_valid:
    print("⚠️ Data has been modified since validation")
```

---

##### load_provenance()

```python
@staticmethod
load_provenance(provenance_file: str) -> Dict
```

**Description**: Load provenance from JSON file.

**Returns**:
- `Dict`: Provenance data

**Example**:
```python
from dqf.utils.provenance import ProvenanceTracker

prov = ProvenanceTracker.load_provenance(
    'provenance/BTC-USD_20260120.json'
)

print(f"Source: {prov['source']}")
print(f"Date range: {prov['date_range']['start']} to {prov['date_range']['end']}")
print(f"Checks run: {', '.join(prov['checks_run'])}")
```

---

### logger.py

#### setup_logger()

```python
setup_logger(
    name: str = 'dqf',
    log_dir: str = 'logs',
    level: int = logging.INFO
) -> logging.Logger
```

**Description**: Configure DQF logging with file and console handlers.

**Parameters**:
- `name` (str): Logger name
- `log_dir` (str): Directory for log files
- `level` (int): Logging level (DEBUG, INFO, WARNING, ERROR)

**Returns**:
- `logging.Logger`: Configured logger

**Example**:
```python
from dqf.utils.logger import setup_logger
import logging

logger = setup_logger(
    name='custom_dqf',
    log_dir='custom_logs',
    level=logging.DEBUG
)

logger.info("Validation started")
logger.warning("Potential issue detected")
logger.error("Critical error occurred")
```

---

## Enums

### CheckStatus

```python
from dqf.core.enums import CheckStatus

CheckStatus.PASS       # 'PASS'
CheckStatus.FAIL       # 'FAIL'
CheckStatus.WARNING    # 'WARNING'
CheckStatus.ERROR      # 'ERROR'
```

**Usage**:
```python
from dqf import DQFValidator, DQFConfig
from dqf.core.enums import CheckStatus

validator = DQFValidator(DQFConfig())
report = validator.validate(data)

# Type-safe comparison
if report.overall_status == CheckStatus.PASS:
    print("✅ Check passed")
elif report.overall_status == CheckStatus.FAIL:
    print("❌ Check failed")

# String comparison also works
if report.overall_status == "PASS":
    print("✅ Check passed")
```

---

### CheckSeverity

```python
from dqf.core.enums import CheckSeverity

CheckSeverity.INFO      # 'INFO'
CheckSeverity.WARNING   # 'WARNING'
CheckSeverity.CRITICAL  # 'CRITICAL'
```

**Usage**:
```python
from dqf.core.enums import CheckSeverity

for result in report.check_results.values():
    if result.severity == CheckSeverity.CRITICAL:
        print(f"🚨 Critical issue: {result.check_name}")
    elif result.severity == CheckSeverity.WARNING:
        print(f"⚠️ Warning: {result.check_name}")
    else:
        print(f"ℹ️ Info: {result.check_name}")
```

---

**End of Part 3: Checks 5-7 + Utils**

**Lines**: ~850
**Next Part**: Configuration Schema + Examples

# DQF API Reference v1.0.0 - Part 4: Configuration + Examples

## Configuration Schema

### Complete YAML Example

```yaml
# DQF Configuration v1.0.0
dqf_version: "1.0.0"

# Global settings
global:
  strict_mode: false        # If true, WARNING → FAIL
  parallel_execution: false # Multi-threading (future feature)

# Check 1: Source Uniqueness
check_1_source:
  enabled: true
  require_metadata: false   # Require source metadata
  max_gap_days: 30          # Max gap between data points

# Check 2: OHLCV Integrity
check_2_integrity:
  enabled: true
  max_violation_rate: 0.01  # 1% violations tolerated
  required_columns:
    - open
    - high
    - low
    - close
    - volume

# Check 3: Calendar Alignment
check_3_calendar:
  enabled: true
  auto_detect: true         # Auto-detect NYSE/CRYPTO/FOREX
  calendar: null            # Override: 'NYSE', 'CRYPTO', 'FOREX'
  strict_mode: false        # Fail on holidays if true

# Check 4: Forward-Fill Limits
check_4_ffill:
  enabled: true
  max_consecutive: 3        # Max consecutive forward-filled days
  severity: 'WARNING'       # 'WARNING' or 'CRITICAL'
  columns_to_check:
    - open
    - high
    - low
    - close

# Check 5: Index Traceability
check_5_trace:
  enabled: true
  require_timezone: true    # Require timezone-aware index
  require_sorted: true      # Require chronological order

# Check 6: Sanity Tests
check_6_sanity:
  enabled: true
  max_return_threshold: 0.20      # 20% max daily return
  min_volume_days: 5              # Require volume >0 for 5+ days
  max_volatility_spike: 5.0       # Max 5× volatility spike
  zero_volume_threshold: 5        # Max consecutive zero volume

# Check 7: Comprehensive Logging
check_7_logging:
  enabled: true
  provenance_dir: 'provenance'    # Output directory
  export_format: 'json'           # Only JSON supported

# Output paths
output:
  log_dir: 'logs'
  report_dir: 'reports'
  provenance_dir: 'provenance'
```

---

### Default Configuration Values

```python
DEFAULT_CONFIG = {
    'check_1_source': {
        'enabled': True,
        'require_metadata': False,
        'max_gap_days': 30
    },
    'check_2_integrity': {
        'enabled': True,
        'max_violation_rate': 0.01,
        'required_columns': ['open', 'high', 'low', 'close', 'volume']
    },
    'check_3_calendar': {
        'enabled': True,
        'auto_detect': True,
        'calendar': None,
        'strict_mode': False
    },
    'check_4_ffill': {
        'enabled': True,
        'max_consecutive': 3,
        'severity': 'WARNING',
        'columns_to_check': ['open', 'high', 'low', 'close']
    },
    'check_5_trace': {
        'enabled': True,
        'require_timezone': True,
        'require_sorted': True
    },
    'check_6_sanity': {
        'enabled': True,
        'max_return_threshold': 0.20,
        'min_volume_days': 5,
        'max_volatility_spike': 5.0,
        'zero_volume_threshold': 5
    },
    'check_7_logging': {
        'enabled': True,
        'provenance_dir': 'provenance',
        'export_format': 'json'
    },
    'output': {
        'log_dir': 'logs',
        'report_dir': 'reports',
        'provenance_dir': 'provenance'
    }
}
```

---

### Configuration Presets

#### Strict Configuration (Production)

```yaml
# config_strict.yaml
dqf_version: "1.0.0"

check_2_integrity:
  enabled: true
  max_violation_rate: 0.0    # Zero tolerance

check_3_calendar:
  enabled: true
  strict_mode: true          # Fail on holidays

check_4_ffill:
  enabled: true
  max_consecutive: 1         # No forward-fill
  severity: 'CRITICAL'

check_5_trace:
  enabled: true
  require_timezone: true

check_6_sanity:
  enabled: true
  max_return_threshold: 0.10  # 10% max return
  zero_volume_threshold: 2    # Max 2 days zero volume
```

**Usage**:
```python
config = DQFConfig.from_yaml("config_strict.yaml")
validator = DQFValidator(config)
```

---

#### Lenient Configuration (Development)

```yaml
# config_lenient.yaml
dqf_version: "1.0.0"

check_2_integrity:
  enabled: true
  max_violation_rate: 0.05   # 5% tolerated

check_3_calendar:
  enabled: true
  strict_mode: false         # Holidays OK

check_4_ffill:
  enabled: true
  max_consecutive: 5         # More lenient
  severity: 'WARNING'

check_6_sanity:
  enabled: true
  max_return_threshold: 0.30  # 30% max return (crypto)
```

---

#### Fast Configuration (Quick Checks Only)

```yaml
# config_fast.yaml
dqf_version: "1.0.0"

check_1_source:
  enabled: true

check_2_integrity:
  enabled: true

check_5_trace:
  enabled: true

# Disable slow checks
check_3_calendar:
  enabled: false

check_4_ffill:
  enabled: false

check_6_sanity:
  enabled: false

check_7_logging:
  enabled: false
```

**Use Case**: Quick validation in CI/CD pipelines

**Note**: In DQF v1.0.0, all checks are always executed regardless of `enabled` flag. Selective execution will be available in v1.1.0. For now, `enabled: false` is documented but not enforced.

---

## Examples & Best Practices

### Example 1: Basic Validation

```python
"""
Example 1: Basic Validation

Demonstrates:
- Loading data with timezone
- Using default configuration
- Interpreting results
- Exporting reports
"""

import pandas as pd
from dqf import DQFValidator, DQFConfig

# Step 1: Load data with timezone
dates = pd.date_range("2024-01-01", periods=188, freq="D", tz="UTC")
data = pd.DataFrame({
    "open": [45000 + i*10 for i in range(188)],
    "high": [45500 + i*10 for i in range(188)],
    "low": [44500 + i*10 for i in range(188)],
    "close": [45200 + i*10 for i in range(188)],
    "volume": [1000000 + i*1000 for i in range(188)],
}, index=dates)

# Step 2: Create validator with default config
config = DQFConfig()
validator = DQFValidator(config)

# Step 3: Validate
report = validator.validate(data, calendar="NYSE")

# Step 4: Interpret results
print(f"Overall Status: {report.overall_status}")
print(f"Checks Passed: {report.checks_passed}/{report.total_checks}")

if report.overall_status == "PASS":
    print("✅ Data validated successfully")
    
    # Access cleaned data
    clean_data = report.cleaned_data
    clean_data.to_csv("btc_usd_clean.csv")
    
else:
    print(f"❌ Validation failed: {len(report.all_issues)} issues")
    
    # Inspect issues
    for issue in report.all_issues:
        print(f"  [{issue.severity}] {issue.check_name}: {issue.message}")

# Step 5: Export reports
report.to_yaml("validation_report.yaml")
report.to_json("validation_report.json")

print("\n✅ Reports exported successfully")
```

---

### Example 2: Custom Configuration

```python
"""
Example 2: Custom Configuration

Demonstrates:
- Loading config from YAML
- Programmatic config creation
- Config modification
- Selective check execution
"""

import pandas as pd
from dqf import DQFValidator, DQFConfig

# Load sample data
data = pd.read_csv("btc_usd.csv", index_col=0, parse_dates=True)
data.index = data.index.tz_localize('UTC')

# Method 1: Load from YAML
config = DQFConfig.from_yaml("config.yaml")
validator = DQFValidator(config)
report = validator.validate(data)

# Method 2: Programmatic config
config = DQFConfig(
    check_2_integrity={
        'enabled': True,
        'max_violation_rate': 0.005  # 0.5% stricter
    },
    check_4_ffill={
        'enabled': True,
        'max_consecutive': 1,        # No forward-fill
        'severity': 'CRITICAL'
    },
    check_6_sanity={
        'enabled': True,
        'max_return_threshold': 0.15  # 15% max return
    }
)

validator = DQFValidator(config)
report = validator.validate(data)

# Method 3: Selective checks (fast validation)
config = DQFConfig(
    check_1_source={'enabled': True},
    check_2_integrity={'enabled': True},
    check_5_trace={'enabled': True},
    # Disable slow checks
    check_3_calendar={'enabled': False},
    check_4_ffill={'enabled': False},
    check_6_sanity={'enabled': False},
    check_7_logging={'enabled': False}
)

validator = DQFValidator(config)
report = validator.validate(data)  # Fast validation (3/7 checks)

print(f"Checks run: {report.total_checks}")
```

---

### Example 3: Batch Processing

```python
"""
Example 3: Batch Processing

Demonstrates:
- Validating multiple symbols
- Filtering clean datasets
- Generating consolidated report
- Error handling
"""

import pandas as pd
from dqf import DQFValidator, DQFConfig
from pathlib import Path

def validate_batch(files, config):
    """Validate multiple datasets."""
    results = {}
    
    for filepath in files:
        symbol = Path(filepath).stem  # Extract symbol from filename
        
        try:
            # Load data
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            data.index = data.index.tz_localize('UTC')
            
            # Validate
            validator = DQFValidator(config)
            report = validator.validate(data, symbol=symbol)
            
            results[symbol] = {
                'status': report.overall_status,
                'report': report,
                'data': data
            }
            
            print(f"✅ {symbol}: {report.overall_status}")
            
        except Exception as e:
            results[symbol] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"❌ {symbol}: ERROR - {e}")
    
    return results

# Usage
files = [
    "data/BTC-USD.csv",
    "data/ETH-USD.csv",
    "data/SPY.csv",
    "data/GLD.csv"
]

config = DQFConfig()
results = validate_batch(files, config)

# Filter clean datasets
clean_datasets = {
    symbol: result['data']
    for symbol, result in results.items()
    if result['status'] == 'PASS'
}

print(f"\n✅ {len(clean_datasets)}/{len(files)} datasets passed validation")

# Export clean datasets
for symbol, data in clean_datasets.items():
    data.to_csv(f"clean_data/{symbol}_clean.csv")

# Generate consolidated report
summary = pd.DataFrame([
    {
        'symbol': symbol,
        'status': result['status'],
        'checks_passed': result['report'].checks_passed if 'report' in result else 0,
        'issues': len(result['report'].all_issues) if 'report' in result else 0
    }
    for symbol, result in results.items()
])

summary.to_csv("batch_summary.csv", index=False)
print("\n✅ Batch processing complete")
```

---

### Example 4: Custom Check

```python
"""
Example 4: Custom Check

Demonstrates:
- Creating custom check class
- Inheriting from BaseCheck
- Using helper methods
- Adding to validator
"""

from dqf import DQFValidator, DQFConfig
from dqf.checks.base import BaseCheck, CheckResult
import pandas as pd

class PumpAndDumpDetector(BaseCheck):
    """Detect pump-and-dump patterns."""
    
    def __init__(self, pump_threshold=0.30, dump_threshold=-0.25):
        super().__init__(
            check_id="check_8_pump_dump",
            check_name="Pump and Dump Detection"
        )
        self.pump_threshold = pump_threshold
        self.dump_threshold = dump_threshold
    
    def run(self, df, **kwargs):
        """Detect pump-and-dump patterns."""
        
        # Validate input
        self._validate_dataframe(df)
        
        # Calculate returns
        returns = df['close'].pct_change()
        
        # Detect pumps (large positive returns)
        pumps = returns > self.pump_threshold
        
        # Detect dumps (large negative returns following pumps)
        dumps = returns < self.dump_threshold
        
        # Find pump-dump patterns (pump followed by dump within 5 days)
        patterns = 0
        for i in range(len(df) - 5):
            if pumps.iloc[i]:
                if dumps.iloc[i+1:i+6].any():
                    patterns += 1
        
        if patterns > 0:
            return self._create_result(
                status='FAIL',
                severity='WARNING',
                message=f'Detected {patterns} potential pump-and-dump patterns',
                details={
                    'pattern_count': patterns,
                    'pump_threshold': self.pump_threshold,
                    'dump_threshold': self.dump_threshold
                }
            )
        
        return self._create_result(
            status='PASS',
            message='No pump-and-dump patterns detected'
        )

# Usage
data = pd.read_csv("suspicious_coin.csv", index_col=0, parse_dates=True)
data.index = data.index.tz_localize('UTC')

config = DQFConfig()
validator = DQFValidator(config)

# Add custom check
pump_dump_detector = PumpAndDumpDetector(
    pump_threshold=0.30,   # 30% pump
    dump_threshold=-0.25   # 25% dump
)
validator.add_custom_check('check_8_pump_dump', pump_dump_detector)

# Validate (7 standard + 1 custom = 8 checks)
report = validator.validate(data)

print(f"Total checks: {report.total_checks}")  # 8
print(f"Status: {report.overall_status}")

# Access custom check result
custom_result = report.check_results['check_8_pump_dump']
if custom_result.status == 'FAIL':
    print(f"⚠️ {custom_result.message}")
```

---

## Best Practices

### Data Preparation

```python
# ✅ GOOD: Timezone-aware data
dates = pd.date_range("2024-01-01", periods=100, tz="UTC")
data = pd.DataFrame({...}, index=dates)

# ❌ BAD: No timezone
dates = pd.date_range("2024-01-01", periods=100)
data = pd.DataFrame({...}, index=dates)

# Fix: Add timezone
data.index = data.index.tz_localize('UTC')
```

---

### Column Naming

```python
# ✅ GOOD: Lowercase column names (case-insensitive)
data.columns = ['open', 'high', 'low', 'close', 'volume']

# ⚠️ ACCEPTABLE: Mixed case (auto-normalized)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# ❌ BAD: Missing required columns
data.columns = ['o', 'h', 'l', 'c', 'v']  # Will fail validation
```

---

### Understanding DQF Output

**IMPORTANT**: DQF v1.0.0 is **validation-only**, not active cleaning.

```python
report = validator.validate(data)

if report.overall_status == 'PASS':
    # cleaned_data is the ORIGINAL data (validated as clean)
    # NOT modified or cleaned by DQF
    clean_data = report.cleaned_data
    
    # This is the same as your input if status is PASS
    assert clean_data.equals(data)  # True
    
else:
    # DQF detected issues but did NOT fix them
    # You must manually clean or reject the data
    print(f"Issues found: {len(report.all_issues)}")
    
    # Option 1: Reject data entirely
    raise ValueError("Data quality check failed")
    
    # Option 2: Manual cleaning based on issues
    for issue in report.all_issues:
        print(f"Fix needed: {issue.message}")
```

**Future**: Active data cleaning will be available in v1.2.0 (auto-repair strategies).

---

### Error Handling

```python
# ✅ GOOD: Comprehensive error handling
try:
    report = validator.validate(data)
    
    if report.overall_status == 'PASS':
        clean_data = report.cleaned_data
        clean_data.to_csv("output.csv")
    else:
        for issue in report.all_issues:
            logger.error(f"{issue.check_name}: {issue.message}")
        
except TypeError as e:
    logger.error(f"Invalid data type: {e}")
except ValueError as e:
    logger.error(f"Invalid data: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

---

### Configuration Management

```python
# ✅ GOOD: Version-controlled config files
# config/prod.yaml    - Production (strict)
# config/dev.yaml     - Development (lenient)
# config/test.yaml    - Testing (fast)

import os
env = os.getenv('ENVIRONMENT', 'dev')
config = DQFConfig.from_yaml(f"config/{env}.yaml")

# ✅ GOOD: Environment-specific overrides
if env == 'prod':
    config.check_2_integrity['max_violation_rate'] = 0.0
```

---

### Provenance Tracking

```python
# ✅ GOOD: Always save provenance for production data
report = validator.validate(data, calendar="NYSE")

if report.overall_status == 'PASS':
    # Save validated data
    data.to_csv("btc_usd_validated.csv")
    
    # Save report + provenance
    report.to_yaml("reports/btc_usd_report.yaml")
    # Provenance auto-saved by check_7_logging
    
    print(f"✅ Provenance: {report.provenance['timestamp']}")
```

---

### Performance Optimization

```python
# For large datasets (>1M rows)

# 1. Note: Selective checks not yet implemented in v1.0.0
# All checks are executed regardless of config
# Feature coming in v1.1.0

# 2. Process in chunks (for memory efficiency)
chunk_size = 100000
results = []

for chunk in pd.read_csv("large.csv", chunksize=chunk_size):
    report = validator.validate(chunk)
    results.append(report)

# 3. Use optimized config for speed
config_fast = DQFConfig(
    check_6_sanity={'enabled': False},  # Statistical checks (slowest)
    check_7_logging={'enabled': False}  # I/O operations
)
# Note: In v1.0.0, these still run but can be disabled in v1.1.0

# Performance expectations (v1.0.0):
# - 100 days: ~1.2s
# - 1,000 days: ~3.5s  
# - 10,000 days: ~25s
```

---

## Performance Notes

**Current Performance** (v1.0.0):
- Small datasets (100-1000 days): < 5 seconds
- Medium datasets (1000-10000 days): < 30 seconds
- Large datasets (>10000 days): Process in chunks recommended

**Bottlenecks**:
- Check 6 (Sanity): Statistical calculations (~35% of time)
- Check 7 (Logging): I/O operations (~15% of time)
- Check 2 (Integrity): Multiple validations (~25% of time)

**Future Optimizations** (v1.1.0+):
- Selective check execution (skip disabled checks)
- Parallel check execution (multi-threading)
- Vectorized operations optimization

---

## Troubleshooting

### Common Errors

#### TypeError: Expected pd.DataFrame

```python
# Error
validator.validate([1, 2, 3])
# TypeError: Expected pd.DataFrame, got list

# Fix
df = pd.DataFrame(data)
validator.validate(df)
```

---

#### ValueError: Missing required columns

```python
# Error
data.columns = ['o', 'h', 'l', 'c', 'v']
validator.validate(data)
# ValueError: Missing required columns: ['open', 'high', 'low', 'close', 'volume']

# Fix
data.columns = ['open', 'high', 'low', 'close', 'volume']
```

---

#### AttributeError: 'str' object has no attribute 'isoformat'

```python
# Error
report.timestamp.isoformat()
# AttributeError: 'str' object has no attribute 'isoformat'

# Fix: timestamp is already a string (ISO 8601 formatted)
print(report.timestamp)  # ✅ Correct
```

---

**End of Part 4: Configuration + Examples**

**Lines**: ~920
**Total API.md**: ~3540 lines (complete)

**Links to Examples**:
- See `examples/01_basic_validation.py` for basic workflow
- See `examples/02_custom_config.py` for 5 configuration patterns
- See `examples/03_batch_processing.py` for multi-symbol validation
- See `examples/04_custom_check.py` for custom check implementation

**API.md v1.0.0 - Complete and Production Ready** ✅
