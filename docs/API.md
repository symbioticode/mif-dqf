# DQF API Reference

**Version**: 1.0.0  
**Last Updated**: January 12, 2026

---

## Complete End-to-End Example

```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

# Load data
data = pd.read_csv("btc_usd.csv", index_col=0, parse_dates=True)

# Custom configuration
config = DQFConfig(
    check_2_integrity={
        'enabled': True,
        'max_violation_rate': 0.005  # 0.5% (stricter than default 1%)
    },
    check_4_ffill={
        'enabled': True,
        'max_consecutive': 1,  # No more than 1 day forward-fill
        'severity': 'CRITICAL'  # Treat as critical if violated
    },
    check_6_sanity={
        'enabled': True,
        'max_return_threshold': 0.15,  # 15% max daily return
        'min_volume_days': 5  # Require volume >0 for 5+ days
    },
    output={
        'log_dir': 'custom_logs',
        'report_dir': 'custom_reports',
        'provenance_dir': 'custom_provenance'
    }
)

# Validate
validator = DQFValidator(config)
report = validator.validate(data)

# Results
print(f"Overall Status: {report.overall_status}")  # PASS or FAIL
print(f"Checks Passed: {report.checks_passed}/{report.total_checks}")
print(f"Issues Detected: {len(report.all_issues)}")

# Individual check results
for check_name, result in report.check_results.items():
    status_icon = "✅" if result.status == "PASS" else "❌"
    print(f"{status_icon} {check_name}: {result.status}")

# Issues (if any)
if report.all_issues:
    print("\nIssues:")
    for issue in report.all_issues:
        print(f"  [{issue.severity}] {issue.check_name}: {issue.message}")

# Access cleaned data (only if PASS)
if report.overall_status == "PASS":
    clean_data = report.cleaned_data
    clean_data.to_csv("btc_usd_clean.csv")
    print("✅ Clean data saved")
else:
    print("❌ Data failed validation - not saving")

# Export reports
report.to_yaml("validation_report.yaml")
report.to_json("validation_report.json")

# Access provenance
provenance = report.provenance
print(f"\nProvenance: {provenance['source']}")
print(f"Timestamp: {provenance['timestamp']}")
```

---

## Core Classes

### DQFValidator

**Description**: Orchestrates all 7 data quality checks.

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
validate(df: pd.DataFrame) -> DQFReport
```

**Description**: Run all enabled checks on DataFrame.

**Parameters**:
- `df` (pd.DataFrame): DataFrame with datetime index and OHLCV columns

**Returns**:
- `DQFReport`: Report object with results and cleaned data

**Raises**:
- `TypeError`: If `df` is not a pandas DataFrame
- `ValueError`: If `df` missing required columns

**Example**:
```python
import pandas as pd

data = pd.read_csv("spy_data.csv", index_col=0, parse_dates=True)
report = validator.validate(data)

if report.overall_status == "PASS":
    print("✅ Validation passed")
else:
    print(f"❌ Validation failed: {len(report.all_issues)} issues")
```

---

#### run_check()

```python
run_check(check_name: str, df: pd.DataFrame) -> CheckResult
```

**Description**: Run a single check by name.

**Parameters**:
- `check_name` (str): Check identifier (e.g., 'check_1_source')
- `df` (pd.DataFrame): DataFrame to validate

**Returns**:
- `CheckResult`: Result of the individual check

**Example**:
```python
# Run only OHLCV integrity check
result = validator.run_check('check_2_integrity', data)
print(f"Status: {result.status}")
print(f"Message: {result.message}")
```

---

#### add_custom_check()

```python
add_custom_check(name: str, check: BaseCheck) -> None
```

**Description**: Add a custom check to the validation pipeline.

**Parameters**:
- `name` (str): Unique identifier for custom check
- `check` (BaseCheck): Instance of custom check class

**Example**:
```python
from dqf.checks.base import BaseCheck, CheckResult

class VolumeSpikesCheck(BaseCheck):
    def run(self, df):
        vol_mean = df['volume'].mean()
        spikes = (df['volume'] > vol_mean * 5).sum()
        
        if spikes > 3:
            return CheckResult(
                status='FAIL',
                severity='WARNING',
                message=f'{spikes} volume spikes detected (>5× mean)'
            )
        return CheckResult(status='PASS')

validator.add_custom_check('check_8_volume_spikes', VolumeSpikesCheck())
report = validator.validate(data)
```

---

### DQFReport

**Description**: Container for validation results.

#### Attributes

```python
overall_status: str         # 'PASS' or 'FAIL'
checks_passed: int          # Number of checks that passed
total_checks: int           # Total number of checks run
check_results: Dict[str, CheckResult]  # Individual results
all_issues: List[CheckIssue]  # All issues across checks
cleaned_data: pd.DataFrame  # Validated DataFrame (if PASS)
provenance: Dict            # Full provenance chain
timestamp: datetime         # Validation timestamp
```

**Example**:
```python
report = validator.validate(data)

print(f"Status: {report.overall_status}")
print(f"Passed: {report.checks_passed}/{report.total_checks}")
print(f"Issues: {len(report.all_issues)}")

# Access individual check
result = report.check_results['check_2_integrity']
print(f"OHLCV Integrity: {result.status}")
```

---

#### to_yaml()

```python
to_yaml(filepath: str) -> None
```

**Description**: Export report as YAML file.

**Parameters**:
- `filepath` (str): Path to output YAML file

**Example**:
```python
report.to_yaml("validation_report.yaml")
```

**Output Format**:
```yaml
overall_status: PASS
checks_passed: 7
total_checks: 7
timestamp: '2026-01-12T14:30:00Z'

check_results:
  check_1_source:
    status: PASS
    severity: INFO
    message: "Source validation passed"
  
  check_2_integrity:
    status: PASS
    severity: INFO
    message: "0 OHLCV violations detected"

all_issues: []

provenance:
  source: "yahoo_finance"
  timestamp: "2026-01-12T14:30:00Z"
  checks_run: 7
```

---

#### to_json()

```python
to_json(filepath: str) -> None
```

**Description**: Export report as JSON file.

**Parameters**:
- `filepath` (str): Path to output JSON file

**Example**:
```python
report.to_json("validation_report.json")
```

---

#### to_dict()

```python
to_dict() -> Dict
```

**Description**: Convert report to Python dictionary.

**Returns**:
- `Dict`: Report as dictionary (JSON-serializable)

**Example**:
```python
report_dict = report.to_dict()
print(report_dict['overall_status'])
```

---

### DQFConfig

**Description**: Configuration manager for DQF validation.

#### Constructor

```python
DQFConfig(**kwargs)
```

**Parameters**: Accepts nested dictionaries for each check configuration.

**Example**:
```python
config = DQFConfig(
    check_1_source={
        'enabled': True,
        'require_metadata': True,
        'max_gap_days': 7
    },
    output={
        'log_dir': 'logs',
        'report_dir': 'reports'
    }
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

**Example**:
```python
# config.yaml
dqf_version: "1.0.0"

checks:
  check_2_integrity:
    enabled: true
    max_violation_rate: 0.01
  
  check_4_ffill:
    enabled: true
    max_consecutive: 3

output:
  log_dir: "logs"
```

```python
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
    'check_2_integrity': {
        'enabled': True,
        'max_violation_rate': 0.005
    }
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
- `bool`: True if valid, raises ValueError if invalid

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
```

---

## Checks

### Check 1: SourceUniquenessCheck

**Purpose**: Validate data comes from single canonical source with proper metadata.

**Parameters**:
```yaml
check_1_source:
  enabled: true
  require_metadata: true   # Require source metadata
  max_gap_days: 30         # Max allowed gap between data points
```

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='INFO' | 'WARNING' | 'CRITICAL',
    message='Validation details',
    details={
        'source': 'yahoo_finance',
        'has_metadata': True,
        'max_gap_detected': 2  # days
    }
)
```

**Example**:
```python
from dqf.checks.check_1_source import SourceUniquenessCheck

check = SourceUniquenessCheck(
    require_metadata=True,
    max_gap_days=7
)

result = check.run(data)
print(f"Status: {result.status}")
print(f"Source: {result.details['source']}")
```

---

### Check 2: OHLCVIntegrityCheck

**Purpose**: Enforce market physics laws (H≥L, H≥O/C, V≥0, no NaN).

**Parameters**:
```yaml
check_2_integrity:
  enabled: true
  max_violation_rate: 0.01  # 1% violations tolerated
  required_columns: ['open', 'high', 'low', 'close', 'volume']
```

**Validation Rules**:
1. `high >= low` (always)
2. `close` ∈ [`low`, `high`] (always)
3. `open` ∈ [`low`, `high`] (warning if violated)
4. `volume >= 0` (always)
5. No NaN in OHLC columns

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='INFO' | 'WARNING' | 'CRITICAL',
    message='X violations detected',
    details={
        'high_low_violations': 0,
        'close_range_violations': 0,
        'nan_count': 0,
        'total_rows': 187
    }
)
```

**Example**:
```python
from dqf.checks.check_2_integrity import OHLCVIntegrityCheck

check = OHLCVIntegrityCheck(max_violation_rate=0.005)
result = check.run(data)

if result.status == 'FAIL':
    print(f"Violations: {result.details['high_low_violations']}")
```

---

### Check 3: CalendarAlignmentCheck

**Purpose**: Detect trading calendar and validate only trading days present.

**Parameters**:
```yaml
check_3_calendar:
  enabled: true
  auto_detect: true        # Auto-detect NYSE/CRYPTO/FOREX
  calendar: null           # Override: 'NYSE', 'CRYPTO', 'FOREX'
  strict_mode: false       # If true, fail on holidays
```

**Calendar Detection Logic**:
1. Check for weekends: if present → CRYPTO (24/7)
2. Check for Friday-Sunday gap: if present → FOREX (24/5)
3. Default: NYSE (weekdays only, major holidays excluded)

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='INFO' | 'WARNING' | 'CRITICAL',
    message='Calendar validation details',
    details={
        'detected_calendar': 'NYSE',
        'weekends_detected': 0,
        'holidays_detected': 2,
        'total_trading_days': 187
    }
)
```

**Example**:
```python
from dqf.checks.check_3_calendar import CalendarAlignmentCheck

check = CalendarAlignmentCheck(auto_detect=True)
result = check.run(data)

print(f"Detected: {result.details['detected_calendar']}")
```

---

### Check 4: ForwardFillLimitsCheck

**Purpose**: Detect excessive forward-filling (data interpolation abuse).

**Parameters**:
```yaml
check_4_ffill:
  enabled: true
  max_consecutive: 3       # Max consecutive forward-filled days
  severity: 'WARNING'      # 'WARNING' or 'CRITICAL'
```

**Detection Logic**:
- Identifies sequences where OHLC values are identical
- Excludes NaN sequences (not forward-fill)
- Reports longest sequence found

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='WARNING' | 'CRITICAL',
    message='X consecutive forward-filled days detected',
    details={
        'max_consecutive_ffill': 2,
        'threshold': 3,
        'sequences_detected': 5
    }
)
```

**Example**:
```python
from dqf.checks.check_4_ffill import ForwardFillLimitsCheck

check = ForwardFillLimitsCheck(max_consecutive=1, severity='CRITICAL')
result = check.run(data)

if result.status == 'FAIL':
    print(f"Max ffill: {result.details['max_consecutive_ffill']} days")
```

---

### Check 5: IndexTraceabilityCheck

**Purpose**: Validate index is unique, chronological, and timezone-aware.

**Parameters**:
```yaml
check_5_index:
  enabled: true
  require_timezone: true   # Require timezone-aware index
  require_sorted: true     # Require chronological order
```

**Validation Rules**:
1. Index must be DatetimeIndex
2. No duplicate timestamps
3. Chronologically sorted (ascending)
4. Timezone-aware (if require_timezone=true)

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='INFO' | 'WARNING' | 'CRITICAL',
    message='Index validation details',
    details={
        'is_datetime_index': True,
        'has_duplicates': False,
        'is_sorted': True,
        'has_timezone': True,
        'timezone': 'UTC'
    }
)
```

**Example**:
```python
from dqf.checks.check_5_index import IndexTraceabilityCheck

check = IndexTraceabilityCheck(require_timezone=True)
result = check.run(data)

print(f"Timezone: {result.details['timezone']}")
```

---

### Check 6: SanityTestsCheck

**Purpose**: Detect statistical anomalies (extreme returns, zero volume, volatility spikes).

**Parameters**:
```yaml
check_6_sanity:
  enabled: true
  max_return_threshold: 0.20   # 20% max daily return
  min_volume_days: 5           # Require volume >0 for 5+ days
  max_volatility_spike: 5.0    # Max 5× volatility spike
```

**Anomalies Detected**:
1. **Extreme Returns**: Daily return > threshold
2. **Zero Volume**: Consecutive days with volume = 0
3. **Volatility Spikes**: Return volatility > N× rolling average

**CheckResult Structure**:
```python
CheckResult(
    status='PASS' | 'FAIL',
    severity='WARNING',  # Always WARNING (statistical, not physical)
    message='X anomalies detected',
    details={
        'extreme_returns': 2,
        'zero_volume_sequences': 1,
        'volatility_spikes': 0,
        'total_anomalies': 3
    }
)
```

**Example**:
```python
from dqf.checks.check_6_sanity import SanityTestsCheck

check = SanityTestsCheck(max_return_threshold=0.15)
result = check.run(data)

if result.details['extreme_returns'] > 0:
    print(f"Warning: {result.details['extreme_returns']} extreme returns")
```

---

### Check 7: ComprehensiveLoggingCheck

**Purpose**: Track complete provenance chain and export as JSON.

**Parameters**:
```yaml
check_7_logging:
  enabled: true
  provenance_dir: 'provenance'  # Output directory
  export_format: 'json'         # Only JSON supported
```

**Provenance Structure**:
```json
{
  "source": "yahoo_finance",
  "symbol": "BTC-USD",
  "timestamp": "2026-01-12T14:30:00Z",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "total_days": 187
  },
  "checks_run": [
    "check_1_source",
    "check_2_integrity",
    "..."
  ],
  "checksums": {
    "close": "a3f2b1c4...",
    "volume": "d5e6f7a8..."
  },
  "statistics": {
    "mean_close": 45234.56,
    "std_close": 3421.78,
    "total_volume": 1234567890
  }
}
```

**Example**:
```python
from dqf.checks.check_7_logging import ComprehensiveLoggingCheck

check = ComprehensiveLoggingCheck(provenance_dir='custom_provenance')
result = check.run(data)

print(f"Provenance saved: {result.details['provenance_file']}")
```

---

## Utils

### calendar.py

#### detect_trading_calendar()

```python
detect_trading_calendar(df: pd.DataFrame) -> str
```

**Description**: Auto-detect trading calendar based on data patterns.

**Returns**:
- `'CRYPTO'`: If weekends present (24/7 trading)
- `'FOREX'`: If Friday-Sunday gaps detected (24/5 trading)
- `'NYSE'`: Default (weekdays only)

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

**Description**: Check if given date is a trading day for calendar.

**Parameters**:
- `date` (pd.Timestamp): Date to check
- `calendar` (str): 'NYSE', 'CRYPTO', or 'FOREX'

**Returns**:
- `bool`: True if trading day, False otherwise

**Example**:
```python
from dqf.utils.calendar import is_trading_day
import pandas as pd

date = pd.Timestamp('2024-12-25')  # Christmas
is_open = is_trading_day(date, calendar='NYSE')
print(is_open)  # False
```

---

### provenance.py

#### ProvenanceTracker

```python
ProvenanceTracker(output_dir: str = 'provenance')
```

**Description**: Tracks data provenance and exports to JSON.

**Methods**:

##### save_provenance()

```python
save_provenance(
    symbol: str,
    df: pd.DataFrame,
    operations: List[Dict]
) -> str
```

**Parameters**:
- `symbol` (str): Ticker symbol
- `df` (pd.DataFrame): Final validated DataFrame
- `operations` (List[Dict]): List of operations applied

**Returns**:
- `str`: Path to saved provenance file

**Example**:
```python
from dqf.utils.provenance import ProvenanceTracker

tracker = ProvenanceTracker(output_dir='custom_provenance')

operations = [
    {'operation': 'fetch_canonical', 'timestamp': '...'},
    {'operation': 'validate_integrity', 'timestamp': '...'}
]

filepath = tracker.save_provenance('BTC-USD', data, operations)
print(f"Saved: {filepath}")
```

---

##### verify_provenance()

```python
@staticmethod
verify_provenance(provenance_file: str, current_df: pd.DataFrame) -> bool
```

**Description**: Verify current DataFrame matches saved provenance.

**Parameters**:
- `provenance_file` (str): Path to provenance JSON
- `current_df` (pd.DataFrame): DataFrame to verify

**Returns**:
- `bool`: True if checksums match, False otherwise

**Example**:
```python
from dqf.utils.provenance import ProvenanceTracker

is_valid = ProvenanceTracker.verify_provenance(
    'provenance/BTC-USD_20260112.json',
    current_data
)

if is_valid:
    print("✅ Data unchanged since validation")
else:
    print("❌ Data has been modified")
```

---

### logger.py

#### setup_logger()

```python
setup_logger(
    name: str = 'dqf',
    log_dir: str = 'logs',
    level: int = logging.DEBUG
) -> logging.Logger
```

**Description**: Configure DQF logging with file and console handlers.

**Parameters**:
- `name` (str): Logger name
- `log_dir` (str): Directory for log files
- `level` (int): Logging level (DEBUG, INFO, WARNING, ERROR)

**Returns**:
- `logging.Logger`: Configured logger instance

**Example**:
```python
from dqf.utils.logger import setup_logger
import logging

logger = setup_logger(
    name='custom_dqf',
    log_dir='custom_logs',
    level=logging.INFO
)

logger.info("Validation started")
logger.warning("Potential issue detected")
```

---

## Data Structures

### CheckResult

**Description**: Result of a single check.

```python
@dataclass
class CheckResult:
    status: str              # 'PASS' or 'FAIL'
    severity: str            # 'INFO', 'WARNING', 'CRITICAL'
    message: str             # Human-readable message
    details: Dict = None     # Optional additional details
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
```

**Example**:
```python
result = CheckResult(
    status='FAIL',
    severity='CRITICAL',
    message='3 OHLCV integrity violations detected',
    details={'high_low_violations': 3}
)

result_dict = result.to_dict()
print(result_dict)
```

---

### CheckIssue

**Description**: Single issue detected during validation.

```python
@dataclass
class CheckIssue:
    check_name: str          # Check identifier
    severity: str            # 'WARNING' or 'CRITICAL'
    message: str             # Issue description
    row_index: int = None    # Optional row index
    column: str = None       # Optional column name
```

**Example**:
```python
issue = CheckIssue(
    check_name='check_2_integrity',
    severity='CRITICAL',
    message='High < Low violation',
    row_index=42,
    column='high'
)

print(f"Issue at row {issue.row_index}: {issue.message}")
```

---

## Configuration Schema

### Complete YAML Example

```yaml
# DQF Configuration v1.0.0
dqf_version: "1.0.0"

# Global settings
global:
  strict_mode: false        # If true, WARNING → FAIL
  parallel_execution: false # Multi-threading (future)

# Check 1: Source Uniqueness
check_1_source:
  enabled: true
  require_metadata: true
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

# Check 5: Index Traceability
check_5_index:
  enabled: true
  require_timezone: true    # Require timezone-aware index
  require_sorted: true      # Require chronological order

# Check 6: Sanity Tests
check_6_sanity:
  enabled: true
  max_return_threshold: 0.20     # 20% max daily return
  min_volume_days: 5             # Require volume >0 for 5+ days
  max_volatility_spike: 5.0      # Max 5× volatility spike

# Check 7: Comprehensive Logging
check_7_logging:
  enabled: true
  provenance_dir: 'provenance'   # Output directory
  export_format: 'json'          # Only JSON supported

# Output paths
output:
  log_dir: 'logs'
  report_dir: 'reports'
  provenance_dir: 'provenance'
```

### Default Values

If not specified, DQF uses these defaults:

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
        'severity': 'WARNING'
    },
    'check_5_index': {
        'enabled': True,
        'require_timezone': True,
        'require_sorted': True
    },
    'check_6_sanity': {
        'enabled': True,
        'max_return_threshold': 0.20,
        'min_volume_days': 5,
        'max_volatility_spike': 5.0
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

**End of API Reference**