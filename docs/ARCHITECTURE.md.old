# DQF Architecture

**Version**: 1.0.0  
**Last Updated**: January 21, 2026

---

## Design Philosophy

### The Ritual of Data Purification

DQF is inspired by systematic purification practices performed before critical operations:

**Historical Precedents**:
- **Medicine (1847)**: Semmelweis - Hand washing before surgery reduced mortality from 18% to 2%
- **Laboratory Science**: Sterile technique before experiments ensures reproducibility
- **Software Engineering**: Input validation before processing prevents catastrophic failures

**Cultural Parallels** (methodological approach):
- **Islam - Wuḍū (الوضوء)**: 7 ablutions performed before Salat (prayer) - without proper purification, prayer is invalid
- **Shinto - Temizuya (手水舎)**: Water purification before entering shrine - cleanses before sacred space
- **DQF - Data Purification Framework**: 7 checks performed before data analysis - without validation, all analysis is invalid

> "Without purification, no sacred act is valid.  
> Without DQF, no analysis is trustworthy."

### Core Principles

**1. Standalone Operation**
- No dependencies on MIF (Metric Integrity Framework)
- No dependencies on DAL (Data Abstraction Layer)
- Self-contained, pip-installable package

**2. Domain-Specific Design**
- Built specifically for OHLCV (Open, High, Low, Close, Volume) financial data
- Understands market physics (H≥L always, Close ∈ [Low, High])
- Knows trading calendars (NYSE, CRYPTO, FOREX)

**3. Reproducibility**
- Same data → Same results (always)
- Complete provenance tracking
- Deterministic validation (no randomness)

**4. Transparency**
- Every decision logged
- Full audit trail
- Checksum verification

---

## System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              INPUT: Raw OHLCV DataFrame                     │
│  (pandas DataFrame with datetime index, OHLCV columns)      │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   DQFConfig (YAML)                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  - Check parameters (thresholds, severity levels)    │ │
│  │  - Enable/disable flags per check                    │ │
│  │  - Output paths (logs, reports, provenance)          │ │
│  │  - Default values for all checks                     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              DQFValidator (Orchestrator)                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Check 1: SourceUniquenessCheck                      │ │
│  │    → Validates single source + metadata              │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 2: OHLCVIntegrityCheck                        │ │
│  │    → Enforces H≥L, H≥O/C, V≥0, no NaN in OHLC       │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 3: CalendarAlignmentCheck                     │ │
│  │    → Detects calendar, validates trading days        │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 4: ForwardFillLimitsCheck                     │ │
│  │    → Detects excessive interpolation                 │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 5: IndexTraceabilityCheck                     │ │
│  │    → Validates unique, chronological, timezone-aware │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 6: SanityTestsCheck                           │ │
│  │    → Detects anomalies (extreme returns, zero vol)   │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Check 7: ComprehensiveLoggingCheck                  │ │
│  │    → Provenance tracking + JSON export               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Error Handling: Try-catch per check (robustness)          │
│  Execution: Sequential (v1.0.0), Parallel (v1.1.0+)        │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      DQFReport                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  - overall_status: PASS/WARNING/FAIL                 │ │
│  │  - checks_passed: N/7                                │ │
│  │  - check_results: {check_name: CheckResult}          │ │
│  │  - all_issues: List[CheckIssue]                      │ │
│  │  - cleaned_data: DataFrame (if PASS)                 │ │
│  │  - provenance: Dict (full chain)                     │ │
│  │                                                       │ │
│  │  Methods:                                            │ │
│  │    - to_yaml() → YAML export                         │ │
│  │    - to_json() → JSON export                         │ │
│  │    - to_dict() → Python dict                         │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           OUTPUT: Validated DataFrame + Report              │
│  - Clean data (if PASS)                                    │
│  - Detailed report (YAML/JSON)                             │
│  - Provenance JSON (full audit trail)                      │
│  - Logs (timestamped, comprehensive)                       │
└─────────────────────────────────────────────────────────────┘
```

---

### Data Flow

1. **Input Stage**:
   - User provides pandas DataFrame (datetime index, OHLCV columns)
   - Optionally provides DQFConfig (defaults used if not)

2. **Configuration Stage**:
   - DQFConfig validates all parameters
   - Sets thresholds, severity levels, output paths
   - Enables/disables specific checks (Note: v1.0.0 runs all checks)

3. **Validation Stage**:
   - DQFValidator runs all 7 checks sequentially
   - Each check returns CheckResult (PASS/FAIL + details)
   - Errors caught per check (robust error handling)

4. **Report Stage**:
   - DQFReport aggregates all CheckResults
   - Determines overall_status (PASS if all enabled checks pass)
   - Generates issues list (all FAIL + WARNING results)

5. **Output Stage**:
   - Export report (YAML/JSON)
   - Save provenance (JSON)
   - Log complete audit trail
   - Return cleaned DataFrame (if PASS)

---

## Core Components

### DQFValidator (Orchestrator)

**Responsibility**: Execute all 7 checks and coordinate results

**Design Pattern**: Strategy Pattern
- BaseCheck defines interface
- Each check implements `run(df) → CheckResult`
- DQFValidator orchestrates execution

**Error Handling Strategy**:
```python
# Each check wrapped in try-catch
try:
    result = check.run(df)
except Exception as e:
    result = CheckResult(
        status='FAIL',
        severity='CRITICAL',
        message=f"Check crashed: {str(e)}"
    )
```

**Why This Approach?**
- **Robustness**: One check failing doesn't crash entire validation
- **Debugging**: Clear error messages per check
- **Extensibility**: Easy to add new checks (inherit BaseCheck)

---

### DQFConfig (Configuration)

**Responsibility**: Validate and store all configuration parameters

**YAML vs TOML Decision**:

| Aspect | YAML | TOML | Decision |
|--------|------|------|----------|
| **Comments** | ✅ Native | ✅ Native | Tie |
| **Hierarchy** | ✅ Natural indentation | ❌ Verbose | YAML wins |
| **Readability** | ✅ Human-friendly | ⚠️ Technical | YAML wins |
| **Standard Library** | ❌ Requires PyYAML | ✅ tomllib (3.11+) | TOML wins |

**Winner**: YAML (readability > stdlib)

**Validation Strategy**:
- All parameters have defaults
- Type checking on load
- Invalid values → clear error messages

**Example Default**:
```yaml
check_2_integrity:
  enabled: true
  max_violation_rate: 0.01  # 1% violations tolerated
  required_columns: ['open', 'high', 'low', 'close', 'volume']
```

---

### DQFReport (Results)

**Responsibility**: Aggregate check results and provide clean export

**Serialization Choices**:

| Format | Pros | Cons | Use Case |
|--------|------|------|----------|
| **YAML** | Human-readable, comments | Slower parsing | Default export |
| **JSON** | Fast, universal | No comments | API integration |
| **Pickle** | Python-native | Not portable | ❌ Rejected |

**Why Not Pickle?**
- Not human-readable
- Version-dependent
- Security risk (arbitrary code execution)

**Export Methods**:
```python
report.to_yaml("report.yaml")  # Default
report.to_json("report.json")  # API-friendly
report.to_dict()               # Python integration
```

---

### BaseCheck (Abstract Base)

**Interface Contract**:
```python
class BaseCheck(ABC):
    @abstractmethod
    def run(self, df: pd.DataFrame) -> CheckResult:
        """
        Execute check on DataFrame.
        
        Returns:
            CheckResult with status (PASS/FAIL) and details
        """
        pass
```

**Extension Points**:
- Inherit BaseCheck
- Implement `run()`
- Return CheckResult
- Register in DQFValidator

**Custom Check Example**:
```python
class CustomVolumeCheck(BaseCheck):
    def __init__(self):
        super().__init__(
            check_id="check_8_volume",
            check_name="Custom Volume Check"
        )
    
    def run(self, df: pd.DataFrame) -> CheckResult:
        if (df['volume'] == 0).sum() > 10:
            return self._create_result(
                status='FAIL',
                severity='WARNING',
                message='More than 10 zero-volume days detected'
            )
        return self._create_result(status='PASS')
```

---

## The 7 Checks

### Design Principles

**1. Single Responsibility**
- Each check validates ONE aspect of data quality
- No overlap between checks
- Clear pass/fail criteria

**2. Independence**
- Checks can run in any order (mostly)
- One check failing doesn't prevent others
- Results are composable

**3. Composability**
- Overall PASS = All enabled checks PASS
- Issues aggregated across all checks
- Severity levels (INFO, WARNING, CRITICAL)

### Check Categories

**Data Provenance** (Origin & Tracking):
- **Check 1**: Source Uniqueness - Single canonical source
- **Check 7**: Comprehensive Logging - Full audit trail

**Data Integrity** (Physical Laws):
- **Check 2**: OHLCV Integrity - Market physics (H≥L, etc.)
- **Check 5**: Index Traceability - Unique, chronological, timezone

**Calendar Logic** (Time Validity):
- **Check 3**: Calendar Alignment - Trading days only (no weekends)

**Quality Heuristics** (Statistical Sanity):
- **Check 4**: Forward-Fill Limits - Detect interpolation abuse
- **Check 6**: Sanity Tests - Anomalies (extreme returns, zero volume)

### Check Ordering

**Current Order** (Sequential Execution):
1. Source Uniqueness (metadata)
2. OHLCV Integrity (physical laws)
3. Calendar Alignment (trading days)
4. Forward-Fill Limits (gaps)
5. Index Traceability (temporal structure)
6. Sanity Tests (statistical)
7. Comprehensive Logging (provenance)

**Why This Order?**
- Metadata checks first (cheap, foundational)
- Physical laws before statistical tests
- Calendar before gap detection (weekends ≠ gaps)
- Logging last (captures all previous checks)

**Can Order Change?**
- Yes, checks are mostly independent
- Exception: Check 3 should precede Check 4 (calendar affects gap detection)
- Future: Parallel execution possible (v1.1.0+)

---

## Technical Decisions

### Decision Table

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|-------------------------|
| **Logging** | stdlib `logging` | No external deps, standard | loguru (more features, but dependency) |
| **Config Format** | YAML | Human-readable, hierarchical | TOML (less readable), JSON (no comments) |
| **Error Handling** | Exception = bug, FAIL = bad data | Clear separation | Everything as exceptions (poor UX) |
| **Column Names** | Case-insensitive (lowercase) | Robustness (Close vs close) | Case-sensitive (fragile) |
| **Violation Counting** | Per violation, not per row | Accurate (1 row = 3+ violations) | Per row (undercounts) |
| **Cleaned Data** | Passthrough (v1.0.0) | No opinion on cleaning strategy | Auto-clean (too opinionated) |
| **Type Hints** | 100% coverage | mypy compatibility, clarity | Partial hints (inconsistent) |
| **Testing** | pytest + fixtures | Industry standard, powerful | unittest (verbose), nose (dead) |

### Rationale Deep Dives

**Why stdlib `logging` over loguru?**
- DQF is a foundation library
- No dependencies = easier adoption
- stdlib logging is sufficient for audit trails
- Users can wrap with loguru if desired

**Why case-insensitive columns?**
- Yahoo Finance returns 'Close'
- Some sources return 'close'
- Normalizing to lowercase avoids fragile assumptions

**Why passthrough cleaned data (v1.0.0)?**
- Cleaning is opinionated (how to handle NaN?)
- v1.0.0: Detect and report
- v1.2.0+: Optional cleaning strategies
- Users maintain control

---

## Extension Points

### Adding Custom Checks

**Step 1**: Inherit BaseCheck
```python
from dqf.checks.base import BaseCheck, CheckResult

class MyCustomCheck(BaseCheck):
    def __init__(self):
        super().__init__(
            check_id="check_8_custom",
            check_name="My Custom Check"
        )
    
    def run(self, df):
        # Your validation logic
        if some_condition:
            return self._create_result(
                status='FAIL',
                message='...'
            )
        return self._create_result(status='PASS')
```

**Step 2**: Register in DQFValidator
```python
validator = DQFValidator(config)
validator.add_custom_check('check_8_custom', MyCustomCheck())
report = validator.validate(df)
```

**Guidelines**:
- Return CheckResult (never raise for data issues)
- Use severity levels appropriately (INFO/WARNING/CRITICAL)
- Provide clear, actionable messages
- Add tests (see `tests/unit/test_custom_check.py`)

---

### Custom Trading Calendars

**Extend calendar.py**:
```python
from dqf.utils.calendar import register_calendar

def my_custom_calendar():
    """Define custom trading days"""
    return pd.DatetimeIndex([...])

register_calendar('CUSTOM', my_custom_calendar)
```

**Use in Check 3**:
```yaml
check_3_calendar:
  enabled: true
  calendar: 'CUSTOM'  # Instead of NYSE/CRYPTO/FOREX
```

---

### Custom Report Formats

**Extend DQFReport**:
```python
from dqf.core.report import DQFReport

class CustomReport(DQFReport):
    def to_html(self) -> str:
        """Export as HTML"""
        return f"<html>...</html>"
```

---

## Performance Considerations

### Bottlenecks

**Large Datasets (>1M rows)**:
- Check 2 (OHLCV Integrity): O(n) comparisons
- Check 6 (Sanity Tests): O(n) statistical calculations

**Mitigation**:
- Use vectorized pandas operations (no Python loops)
- Consider sampling for Check 6 (future optimization)

**Memory Usage**:
- Full DataFrame kept in memory (v1.0.0)
- Provenance tracking adds ~10% overhead
- Future: Streaming validation (chunked processing)

### Optimization Strategies

**Current (v1.0.0)**:
- Vectorized operations (pandas/numpy)
- Minimal copying (views where possible)
- Sequential execution (all checks run)

**Future (v1.1.0+)**:
- Multi-threading (checks independent)
- Selective execution (`enabled` flag enforced)
- Chunked processing (streaming)

### Scalability

**v1.0.0 Performance**:
- Single-threaded validation
- Full dataset in memory
- Sequential check execution

**Target**: 1,000 days in <5 seconds (v1.0.0)  
**Achieved**: 1,000 days in ~3.5 seconds

**v1.1.0+ Goals**:
- 10,000 days in <30 seconds (multi-threaded)
- 100,000 days in <5 minutes (streaming + optimization)

---

## Testing Strategy

### Unit Tests (96 tests)

**Per Check** (10-15 tests each):
- PASS scenarios (clean data)
- FAIL scenarios (corrupted data)
- Edge cases (empty df, single row, etc.)
- Configuration variations

**Utils** (calendar, provenance):
- Function-level tests
- Edge cases (timezone, daylight saving)

**Coverage Target**: 90%+ per module

### Integration Tests (8 tests)

**End-to-End Workflows**:
- Full validation pipeline (7 checks)
- Config loading (YAML)
- Report generation (YAML/JSON)
- Error scenarios (check crashes)

**Fixtures**:
- Clean OHLCV data (187 days)
- Corrupted data (H<L violations)
- Missing data (NaN in OHLC)

**Coverage Target**: 95%+ critical paths

### Test Coverage (Current)

```
Overall:          77%
check_1_source:   79%
check_2_integrity: 92%
check_3_calendar:  85%
check_4_ffill:     93%
check_5_index:     81%
check_6_sanity:    90%
check_7_logging:   84%
validator.py:      65%
report.py:         79%
config.py:         31%
```

**Critical Paths**: High coverage
- DQFValidator.validate(): Well tested
- DQFReport.to_yaml(): Well tested
- BaseCheck.run(): Well tested

---

## Future Architecture

### v1.1.0: Performance & Selective Execution (Q1 2026)

**Selective Check Execution**:
```yaml
# Enforced in v1.1.0 (not in v1.0.0)
check_6_sanity:
  enabled: false  # Will actually skip check
```

**Multi-threading**:
```python
# Checks run in parallel (independent)
config = DQFConfig(parallel=True)
validator = DQFValidator(config)
report = validator.validate(data)  # 3× faster
```

---

### v1.2.0: Active Data Cleaning (Q1 2026)

**Current**: DQF detects issues, reports them, passes through data  
**v1.2.0**: DQF optionally cleans data based on strategies

**Cleaning Strategies**:
```yaml
cleaning:
  enabled: true
  strategies:
    forward_fill:
      max_consecutive: 1
      method: 'linear'  # or 'nearest', 'polynomial'
    
    calendar_alignment:
      action: 'drop'  # or 'keep', 'flag'
    
    integrity_violations:
      action: 'drop'  # or 'interpolate', 'flag'
```

**Diff Reports**:
- Before/after comparison
- Rows modified/dropped
- Cleaning decisions logged

---

### v2.0.0: DAL Integration (Q2 2026)

**Goal**: DQF called automatically by Data Abstraction Layer

**Interface**:
```python
from dal import DataFetcher
from dqf import DQFValidator

# DAL fetches data
fetcher = DataFetcher(source='yahoo', symbol='BTC-USD')
raw_data = fetcher.fetch(start='2024-01-01', end='2024-12-31')

# DQF validates automatically
validated_data = fetcher.get_validated()  # DQF ran internally

# Provenance chain
provenance = fetcher.get_provenance()
# → {source: 'yahoo', dqf_status: 'PASS', checks_passed: 7}
```

**Provenance Chain**:
- DAL → DQF → MIF (full lineage)
- Each layer adds metadata
- Complete audit trail (source to certification)

---

### v3.0.0: MIF Integration (Q2 2026)

**Layer -1 Positioning**:

```
┌─────────────────────────────────────────────┐
│  MIF Certification (Layers 1-5)            │
│  - Mathematical Limits                      │
│  - Metric Classification                    │
│  - Validation (4 Phases)                    │
│  - Bias Detection                           │
│  - Certification Report                     │
└──────────────────┬──────────────────────────┘
                   ↑
         (Only if DQF PASS)
                   ↓
┌─────────────────────────────────────────────┐
│  DAL (Layer 0)                              │
│  - Multi-source abstraction                 │
│  - Cache management                         │
│  - Cross-validation                         │
└──────────────────┬──────────────────────────┘
                   ↑
         (Calls DQF internally)
                   ↓
┌─────────────────────────────────────────────┐
│  DQF (Layer -1) ← FOUNDATION                │
│  - 7 Checks validation                      │
│  - Provenance tracking                      │
│  - Data certification                       │
└─────────────────────────────────────────────┘
```

**Certification Workflow**:
1. User submits strategy to MIF
2. MIF requests data from DAL
3. DAL fetches data, calls DQF
4. If DQF FAIL → MIF rejects (no certification possible)
5. If DQF PASS → MIF proceeds with Layers 1-5

**Bundle Contents**:
- certification.yaml (MIF Layers 1-5)
- dqf_certification.yaml (Layer -1)
- provenance.json (full chain)
- test_results.parquet (MIF tests)

---

**End of ARCHITECTURE.md**

**Version**: 1.0.0  
**Last Updated**: January 21, 2026  
**Status**: Production Ready