# DQF Troubleshooting Guide

**Version**: 1.1.0  
**Last Updated**: April 12, 2026

---

## Common Errors

### 1. TypeError: Expected DataFrame, got ...

**Error Message**:
```
TypeError: validate() expected pandas.DataFrame, got <class 'NoneType'>
```

**Cause**: Passing wrong data type to validator (None, list, dict, etc.)

**Solution**:
```python
# ❌ WRONG
data = None
validator.validate(data)  # Error!

# ✅ CORRECT
import pandas as pd
data = pd.read_csv("data.csv", index_col=0, parse_dates=True)
validator.validate(data)
```

**Debugging**:
```python
print(type(data))  # Should be: <class 'pandas.core.frame.DataFrame'>
print(isinstance(data, pd.DataFrame))  # Should be: True
```

---

### 2. ValueError: Missing required columns

**Error Message**:
```
ValueError: Missing required columns: ['close', 'volume']
```

**Cause**: DataFrame doesn't have required OHLCV columns

**Common Reason**: Case-sensitive column names

**Solution**:
```python
# Check columns
print(data.columns.tolist())
# Output: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

# DQF expects lowercase
data.columns = [col.lower() for col in data.columns]
print(data.columns.tolist())
# Output: ['date', 'open', 'high', 'low', 'close', 'volume']

# Now validate
report = validator.validate(data)
```

**Alternative**: Rename columns explicitly
```python
data.rename(columns={
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'Volume': 'volume'
}, inplace=True)
```

---

### 3. DQFConfig: missing or invalid mode

**Error Message**:
```
TypeError: config must be a DQFConfig instance ...
TypeError: mode must be a DQFMode instance ...
```

**Cause**: `DQFConfig()` without `mode` parameter, or passing a raw string.

**Solution**:
```python
# ❌ WRONG (v1.0 style — mode has no default in v1.1)
config = DQFConfig()
config = DQFConfig(mode="CERTIFICATION")  # string not accepted

# ✅ CORRECT
from dqf import DQFConfig, DQFMode
config = DQFConfig(mode=DQFMode.CERTIFICATION)
config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
```

**Common YAML mistake**:
```yaml
# ❌ WRONG (old v1.0 schema)
check_2_integrity:
  max_violation_rate: 0.01

# ✅ CORRECT (v1.1 schema)
mode: CERTIFICATION
c4_max_consecutive_ffill: 3
c4_warn_threshold: 2
```

**Validation Tool**:
```python
from dqf import DQFConfig, DQFMode

try:
    config = DQFConfig.from_yaml("config.yaml")
    print(f"✅ Config valid — mode={config.mode.value}")
except (TypeError, ValueError) as e:
    print(f"❌ Config error: {e}")
```

---

### 4. VOID status — CORE check failure

**Error Message**:
```
DQFReport: overall_status=VOID, precondition_gate=0.0
```

**How to diagnose**:
```python
report = validator.validate(data, calendar="NYSE")

print(f"Status : {report.overall_status}")      # VOID
print(f"Gate   : {report.precondition_gate}")    # 0.0
print(f"CORE   : {report.core_results}")         # {'C2': 'FAIL', ...}
print(f"ADVISORY: {report.advisory_results}")

# Human-readable breakdown
report.print_summary()
```

**Common CORE FAIL reasons**:

**C2 (OHLCV Integrity)**:
- `high < low` on any bar (data corruption)
- `close` outside `[low, high]`
- NaN in OHLC columns

**C3 (Calendar Alignment)** — CERTIFICATION mode only:
- `calendar=None` → `ERROR_MISSING_METADATA`
- Unrecognised calendar name → `FAIL`
- Weekend bars in NYSE/LSE/EURONEXT/FOREX_245 data → `WARN` (not VOID)

**C5 (Index Traceability)**:
- Duplicate timestamps
- Non-chronological index
- Timezone-naive DatetimeIndex

**ADVISORY WARN reasons** (→ WARNING, not VOID):

**C4 (Forward-Fill)**:
- Consecutive identical values > `c4_warn_threshold`
- More than `c4_max_consecutive_ffill` → FAIL (escalates to VOID)

---

### 5. ImportError: No module named 'dqf'

**Error Message**:
```
ImportError: No module named 'dqf'
```

**Cause**: DQF not installed or wrong Python environment

**Solution**:
```bash
# Verify Python environment
which python  # Should be your venv/bin/python

# Install DQF
pip install -e .

# Verify installation
python -c "from dqf import DQFValidator; print('✅ Installed')"
```

**If using virtual environment**:
```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install
pip install -e .
```

---

## Performance Issues

### Slow validation (large datasets)

**Symptom**: Validation takes >30 seconds for 1M rows

**Profiling**:
```python
import time

start = time.time()
report = validator.validate(data)
elapsed = time.time() - start

print(f"Validation took {elapsed:.2f} seconds")
print(f"Rows processed: {len(data)}")
print(f"Speed: {len(data)/elapsed:.0f} rows/sec")
```

**Optimization Strategies**:

**1. Sample large datasets** (DIAGNOSTIC mode for speed):
```python
# For initial validation, sample 10% in DIAGNOSTIC mode
from dqf import DQFConfig, DQFMode, DQFValidator
config    = DQFConfig(mode=DQFMode.DIAGNOSTIC)
validator = DQFValidator(config)

sample_data = data.sample(frac=0.1, random_state=42)
report = validator.validate(sample_data)

# If not VOID, validate full dataset in CERTIFICATION mode
if report.overall_status != 'VOID':
    cert_config    = DQFConfig(mode=DQFMode.CERTIFICATION)
    cert_validator = DQFValidator(cert_config)
    full_report    = cert_validator.validate(data, calendar="NYSE")
```

**3. Chunked processing**:
```python
# Process in chunks for memory efficiency
chunk_size = 100000
results = []

for chunk in pd.read_csv("large.csv", chunksize=chunk_size):
    report = validator.validate(chunk)
    results.append(report)
```

**Expected Performance** (v1.1.0 — C6/C7 removed):
- 100 days:    ~0.6s
- 1,000 days:  ~2.0s
- 10,000 days: ~15s

---

### High memory usage

**Symptom**: Validation uses >5GB RAM for 1M row dataset

**Monitoring**:
```python
import psutil
import os

process = psutil.Process(os.getpid())
mem_before = process.memory_info().rss / 1024 / 1024  # MB

report = validator.validate(data)

mem_after = process.memory_info().rss / 1024 / 1024  # MB
print(f"Memory used: {mem_after - mem_before:.2f} MB")
```

**Reducing Footprint**:

**1. Drop unnecessary columns before validation**:
```python
# Keep only OHLCV
data_minimal = data[['open', 'high', 'low', 'close', 'volume']]
report = validator.validate(data_minimal)
```

**2. Use appropriate dtypes**:
```python
# Convert to float32 (instead of float64)
for col in ['open', 'high', 'low', 'close']:
    data[col] = data[col].astype('float32')

# Convert volume to int32
data['volume'] = data['volume'].astype('int32')
```

**3. Clear provenance after validation** (if not needed):
```python
report = validator.validate(data)

# Clear provenance to free memory
report.provenance = None
```

---

## Configuration Issues

### YAML syntax errors

**Error Message**:
```
yaml.scanner.ScannerError: while scanning for the next token
found character '\t' that cannot start any token
```

**Common Mistakes**:

**1. Using tabs instead of spaces**:
```yaml
# ❌ WRONG (tabs)
check_2_integrity:
	max_violation_rate: 0.01  # Tab character

# ✅ CORRECT (spaces)
check_2_integrity:
  max_violation_rate: 0.01  # Two spaces
```

**2. Missing quotes around strings with special chars**:
```yaml
# ❌ WRONG
output:
  log_dir: logs/2024-01-12  # Hyphen causes issues

# ✅ CORRECT
output:
  log_dir: "logs/2024-01-12"
```

**3. Incorrect indentation**:
```yaml
# ❌ WRONG
check_2_integrity:
max_violation_rate: 0.01  # No indentation

# ✅ CORRECT
check_2_integrity:
  max_violation_rate: 0.01
```

**Validation Tool**:
```bash
# Use yamllint (optional)
pip install yamllint
yamllint config.yaml
```

---

### Understanding VOID vs WARNING

In v1.1, the overall status is no longer binary PASS/FAIL.

| Status | Gate | Meaning |
|--------|------|---------|
| `CERTIFIED` | 1.0 | All CORE pass, no advisory warns |
| `WARNING`   | ≤0.8 | All CORE pass, at least one advisory WARN |
| `VOID`      | 0.0 | At least one CORE check FAIL or ERROR |

```python
report = validator.validate(data, calendar="NYSE")

if report.overall_status == "VOID":
    # CORE failure — data unsafe
    print(f"CORE failures: {report.core_results}")

elif report.overall_status == "WARNING":
    # Advisory issue — data usable but flagged
    print(f"Advisory: {report.advisory_results}")
    print(f"MPI: {report.purity_index:.1f}/100")
    print(f"Gate: {report.precondition_gate}")  # ≤ 0.8

else:  # CERTIFIED
    print(f"Certified — MPI={report.purity_index:.1f}  UID={report.mif_uid}")
```

> **Removed in v1.1**: `report.checks_passed`, `report.total_checks`,
> `report.all_issues`, `report.check_results`, `report.timestamp`.
> Use `report.core_results`, `report.advisory_results`, `report.purity_index` instead.

---

## Data Quality Issues

### Too many FAIL results

**Symptom**: 5+ checks failing, hundreds of issues

**Likely Cause**: Data is genuinely corrupted, OR thresholds too strict

**Diagnosis**:
```python
report = validator.validate(data)

# Print all issues
for issue in report.all_issues:
    print(f"[{issue.severity}] {issue.check_name}: {issue.message}")

# Count by severity
critical = sum(1 for i in report.all_issues if i.severity == 'CRITICAL')
warning = sum(1 for i in report.all_issues if i.severity == 'WARNING')

print(f"\nCRITICAL: {critical}")
print(f"WARNING: {warning}")
```

**Solution**:

**If many CRITICAL issues** → Data is corrupted
```python
# Inspect raw data
print(data.head(20))
print(data.describe())

# Check for common corruption
print("NaN counts:", data.isnull().sum())
print("High < Low violations:", (data['high'] < data['low']).sum())
```

**If many WARNING issues** → Adjust thresholds
```yaml
# Relax thresholds
check_2_integrity:
  max_violation_rate: 0.02  # 2% instead of 1%

check_6_sanity:
  max_return_threshold: 0.30  # 30% instead of 20%
```

---

### False positives

**Symptom**: Check fails but data looks correct

**Example**: Check 4 (Forward-Fill) fails on legitimate duplicate prices

**Understanding Severity Levels**:
- **INFO**: Informational, always pass
- **WARNING**: Suspicious, but not fatal (still PASS overall)
- **CRITICAL**: Fatal, overall status = FAIL

**Solution**: Adjust severity
```yaml
check_4_ffill:
  enabled: true
  max_consecutive: 3
  severity: 'WARNING'  # Instead of 'CRITICAL'
```

**Result**:
- Check still runs
- Issues reported
- Overall status = PASS (if only warnings)

---

## Integration Issues

### Import errors (Python path)

**Error Message**:
```
ModuleNotFoundError: No module named 'dqf.checks'
```

**Cause**: DQF not properly installed or PYTHONPATH issues

**Solution**:
```bash
# Reinstall in development mode
pip install -e .

# Verify installation
pip show dqf

# Check site-packages
python -c "import site; print(site.getsitepackages())"
```

**If using Jupyter**:
```bash
# Install in Jupyter kernel
python -m ipykernel install --user --name=dqf_env
```

---

### Version conflicts (dependencies)

**Error Message**:
```
ERROR: pip's dependency resolver does not currently take into account 
all the packages that are installed. pandas 2.0.0 requires numpy>=1.20.0, 
but you have numpy 1.19.5
```

**Solution**:
```bash
# Update all dependencies
pip install --upgrade pandas numpy pyyaml python-dateutil

# Or use requirements.txt
pip install -r requirements.txt --upgrade
```

**Check versions**:
```python
import pandas as pd
import numpy as np
import yaml

print(f"pandas: {pd.__version__}")
print(f"numpy: {np.__version__}")
print(f"pyyaml: {yaml.__version__}")
```

**Required versions** (minimum):
- pandas >= 2.0.0
- numpy >= 1.24.0
- pyyaml >= 6.0
- python-dateutil >= 2.8.0

---

## FAQ

### Q: Can I disable specific checks?

**A**: In v1.0.0, all checks always run. Selective execution will be available in v1.1.0.

```yaml
# v1.0.0: This is documented but not enforced
check_6_sanity:
  enabled: false  # Check still runs
```

**Workaround**: Use report filtering:
```python
report = validator.validate(data)

# Filter out specific checks from analysis
relevant_checks = {
    name: result 
    for name, result in report.check_results.items() 
    if name != 'check_6_sanity'
}
```

---

### Q: How to add custom checks?

**A**: Inherit `BaseCheck` and add to validator

```python
from dqf.checks.base import BaseCheck, CheckResult

class MyCustomCheck(BaseCheck):
    def __init__(self):
        super().__init__(
            check_id="check_8_custom",
            check_name="My Custom Check"
        )
    
    def run(self, df, **kwargs):
        # Your logic
        if some_condition:
            return self._create_result(
                status='FAIL',
                message='...',
                severity='WARNING'
            )
        return self._create_result(status='PASS')

# Add to validator
validator = DQFValidator(config)
validator.add_custom_check('check_8_custom', MyCustomCheck())
```

See `examples/04_custom_check.py` for complete guide.

---

### Q: What's the performance on large datasets?

**A**: Approximately:
- 100 days: ~1.2s
- 1,000 days: ~3.5s
- 10,000 days: ~25s

**Bottlenecks**:
- Check 6 (Sanity): Statistical calculations (~35%)
- Check 7 (Logging): I/O operations (~15%)
- Check 2 (Integrity): Multiple validations (~25%)

---

### Q: Can I use DQF in production?

**A**: Yes, v1.0.0 is production-ready:
- 104 tests (100% passing)
- 77% coverage
- Type hints (mypy compatible)
- Robust error handling
- Complete provenance tracking

**Recommendation**: Run as pre-processing step before live trading.

---

### Q: Does DQF clean data automatically?

**A**: No (v1.0.0). DQF validates and reports issues.

**Current Behavior**:
```python
report = validator.validate(data)

if report.overall_status == 'PASS':
    # cleaned_data is the ORIGINAL data (validated as clean)
    # NOT modified or cleaned by DQF
    clean_data = report.cleaned_data
    assert clean_data.equals(data)  # True
```

**Future** (v1.2.0): Optional auto-cleaning mode will be available.

**Current workaround**: Use report to identify issues, clean manually.

---

### Q: How to report bugs?

**A**: GitHub Issues with:
1. DQF version (`pip show dqf`)
2. Python version (`python --version`)
3. Minimal reproducible example
4. Full error traceback

**Template**:
```markdown
**DQF Version**: 1.0.0
**Python Version**: 3.10.8
**OS**: Ubuntu 22.04

**Issue**: Check 2 fails on valid data

**Reproducible Example**:
```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

data = pd.DataFrame({...})
validator = DQFValidator(DQFConfig())
report = validator.validate(data)
# Error occurs here
```

**Error Traceback**:
```
Traceback (most recent call last):
  ...
```
```

---

### Q: Can I validate multiple symbols in batch?

**A**: Yes, loop over symbols:

```python
symbols = ['BTC-USD', 'ETH-USD', 'SPY']
reports = {}

for symbol in symbols:
    data = load_data(symbol)
    report = validator.validate(data)
    reports[symbol] = report
    
    print(f"{symbol}: {report.overall_status}")
```

See `examples/03_batch_processing.py` for complete example.

---

### Q: Does DQF work with non-OHLCV data?

**A**: No, DQF is specifically designed for OHLCV financial data.

For other data types, you'd need to:
1. Create custom checks (inherit `BaseCheck`)
2. Disable OHLCV-specific checks (Check 2, 3, 6)

**Better approach**: Use pandas-based validation tools for generic data.

---

### Q: How accurate is calendar detection (Check 3)?

**A**: Very accurate for standard calendars:
- **CRYPTO**: 100% (weekends present)
- **NYSE**: 95%+ (weekday-only pattern)
- **FOREX**: 90%+ (Friday-Sunday gap)

**Edge cases**: Holidays may be misclassified. Use explicit calendar override if needed:

```yaml
check_3_calendar:
  auto_detect: false
  calendar: 'NYSE'  # Force NYSE calendar
```

---

### Q: What's the difference between WARNING and CRITICAL?

**A**:
- **WARNING**: Suspicious but not fatal (overall status can still be PASS)
- **CRITICAL**: Fatal error (overall status = FAIL)

**Example**:
```python
# 1 CRITICAL issue → overall FAIL
# 10 WARNING issues → overall PASS (if all checks with CRITICAL pass)
```

---

## Getting Help

### Debug Mode

**Enable verbose logging**:
```python
import logging
from dqf.utils.logger import setup_logger

logger = setup_logger(level=logging.DEBUG)

# Now validator will log everything
validator = DQFValidator(config)
report = validator.validate(data)
```

**Check log file**:
```bash
cat logs/dqf_20260121_143022.log
```

---

### Support Channels

- **GitHub Issues**: [github.com/symbioticode/mif-dqf/issues](https://github.com/symbioticode/mif-dqf/issues)
- **GitHub Discussions**: [github.com/symbioticode/mif-dqf/discussions](https://github.com/symbioticode/mif-dqf/discussions)
- **Email**: corail.synergia@proton.me

---

### Before Asking for Help

**Checklist**:
- [ ] Read relevant documentation section
- [ ] Check this troubleshooting guide
- [ ] Enable debug logging
- [ ] Create minimal reproducible example
- [ ] Check GitHub Issues (maybe already reported)

---

## Known Limitations

### v1.0.0 Limitations

**Selective check execution**:
- All checks always run regardless of `enabled` flag
- Feature coming in v1.1.0

**No active data cleaning**:
- DQF detects issues but doesn't fix them
- Users must clean data manually
- **Coming in v1.2.0**: Optional auto-cleaning mode

**Single-threaded validation**:
- All checks run sequentially
- Large datasets (>10M rows) may be slow
- **Coming in v1.1.0**: Multi-threaded execution

**Calendar detection limitations**:
- Works well for standard calendars (NYSE, CRYPTO, FOREX)
- Custom calendars require manual override
- Holiday detection is heuristic (not exhaustive)

---

### Planned Features (Roadmap)

**v1.1.0** (Q1 2026):
- Performance optimization (multi-threading)
- Selective check execution (`enabled` flag enforced)
- Enhanced calendar detection

**v1.2.0** (Q1 2026):
- Active data cleaning mode
- Configurable cleaning strategies
- Before/after diff reports

**v2.0.0** (Q2 2026):
- DAL integration (auto-validation)
- Streaming data support
- MIF compatibility layer

---

**End of Troubleshooting Guide**

**Last Updated**: January 21, 2026  
**Version**: 1.0.0  
**Status**: Production Ready