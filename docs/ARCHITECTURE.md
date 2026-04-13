# DQF Architecture

**Version**: 1.1.0  
**Last Updated**: 2026-04-06

> **Design decisions are now governed by [DQF_SPECIFICATION.md](./DQF_SPECIFICATION.md).**
> This document covers implementation rationale and internal component design.
> In case of conflict, DQF_SPECIFICATION.md takes precedence.

---

## Design Philosophy

### The Ritual of Data Purification

DQF is inspired by systematic purification practices performed before critical operations:

**Historical Precedents**:
- **Medicine (1847)**: Semmelweis - Hand washing before surgery reduced mortality from 18% to 2%
- **Laboratory Science**: Sterile technique before experiments ensures reproducibility
- **Software Engineering**: Input validation before processing prevents catastrophic failures

**Cultural Parallels** (methodological approach):
- **Islam - Wuḍū (الوضوء)**: Ritual ablution before Salat (prayer) - without proper purification, prayer is invalid
- **Shinto - Temizuya (手水舎)**: Water purification before entering shrine - cleanses before sacred space
- **DQF - Data Purification Framework**: Systematic checks before data analysis - without validation, all analysis is invalid

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

### High-Level Component Diagram (v1.1)

```
┌─────────────────────────────────────────────────────────────┐
│              INPUT: Raw OHLCV DataFrame                     │
│  (pandas DataFrame with tz-aware DatetimeIndex, OHLCV)      │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│          DQFConfig(mode=DQFMode.CERTIFICATION|DIAGNOSTIC)   │
│  - mode:                    REQUIRED — no default           │
│  - c4_max_consecutive_ffill  default 3                      │
│  - c4_warn_threshold         default 2                      │
│  - c1_enabled                default False (DAL pending)    │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              DQFValidator (Orchestrator)                    │
│                                                             │
│  CORE checks  (failure → STATUS_VOID, gate = 0.0)          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  C2: IntegrityCheck                                  │ │
│  │    → Enforces H≥L, H≥O/C, V≥0, no NaN in OHLC       │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  C3: CalendarAlignmentCheck                          │ │
│  │    → CERT: calendar required; DIAG: auto-detect      │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  C5: IndexTraceabilityCheck                          │ │
│  │    → Unique, chronological, timezone-aware index     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ADVISORY checks  (warn → STATUS_WARNING, gate ≤ 0.8)      │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  C1: SourceUniquenessCheck  [SKIP in Phase 1]        │ │
│  │    → Single canonical source + metadata              │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  C4: ForwardFillCheck                                │ │
│  │    → Detects consecutive identical values (ffill)    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  PROD seal  (injected after loop — not a data check)       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  core_results["PROD"] = "PASS"  always                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Error Handling: try-catch per check → STATUS_ERROR        │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              PRODEnvelope → MIF-Lite manifest               │
│  - MIF-UID   = sha256(data_hash ‖ version ‖ cal ‖ mode)    │
│  - MPI       = 100 × (1 − Σ(wᵢ × Nᵢ) / N_total)          │
│  - gate      = 1.0 (CERT) | 0.8 (WARN, MPI-capped) | 0.0  │
│  - sig type  = "sha256_provisional" (Phase 1)              │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  DQFReport (.mif.json)                      │
│  - overall_status:   CERTIFIED | WARNING | VOID            │
│  - purity_index:     0.0 – 100.0  (MPI)                    │
│  - precondition_gate: 0.0 | 0.8 | 1.0                      │
│  - mif_uid:          sha256:...  (deterministic)            │
│  - core_results:     {C2, C3, C5, PROD}                    │
│  - advisory_results: {C1, C4}                              │
│  - vitality_label:   EXCELLENT | GOOD | DEGRADED | CRITICAL │
│  - cleaned_data:     validated DataFrame (passthrough Ph.1) │
│                                                             │
│  Methods (return str, NOT write file):                     │
│    - to_json()  → JSON string of manifest                  │
│    - to_yaml()  → YAML string of manifest                  │
│    - print_summary() → human-readable console output       │
└─────────────────────────────────────────────────────────────┘
```

---

### Data Flow

1. **Input Stage**:
   - User provides pandas DataFrame (tz-aware DatetimeIndex, OHLCV columns)
   - Provides `DQFConfig(mode=DQFMode.CERTIFICATION|DIAGNOSTIC)` — mode is mandatory

2. **Configuration Stage**:
   - `DQFConfig.__post_init__` validates mode and c4 thresholds
   - `DQFValidator._init_checks()` instantiates C2, C3, C5, C4 (and C1 if enabled)

3. **Validation Stage**:
   - CORE checks (C2, C3, C5) run unconditionally
   - ADVISORY checks (C4, C1) run and produce warnings but never block
   - Each check returns `CheckResult` with `interventions: InterventionLog`
   - Errors caught per check → `STATUS_ERROR` (treated as CORE failure)
   - `core_results["PROD"] = "PASS"` injected after loop (envelope seal)

4. **MPI + Manifest Stage** (`PRODEnvelope.build()`):
   - `InterventionLog` aggregated across all checks
   - `compute_mpi(log, n_total_points)` → purity_index ∈ [0, 100]
   - Overall status: CORE FAIL/ERROR → VOID; ADVISORY WARN → WARNING; else CERTIFIED
   - `precondition_gate` derived from status (WARNING gate capped by MPI/100)
   - MIF-UID = SHA-256(data_hash ‖ dqf_version ‖ calendar ‖ mode)
   - Provisional signature = SHA-256(mif_uid)

5. **Output Stage**:
   - `DQFReport(manifest=..., cleaned_data=df)` returned
   - Caller serialises with `to_json()` / `to_yaml()` (both return strings)

---

## Core Components

### DQFValidator (Orchestrator)

**Responsibility**: Execute CORE + ADVISORY checks and coordinate results through PRODEnvelope

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

**Example (v1.1)**:
```yaml
# config.yaml
mode: CERTIFICATION
c4_max_consecutive_ffill: 3
c4_warn_threshold: 2
```

```python
config = DQFConfig.from_yaml("config.yaml")
# DQFConfig(mode=DQFMode.CERTIFICATION, c4_max_consecutive_ffill=3, c4_warn_threshold=2)
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

**Export Methods** (both return strings in v1.1 — not file writes):
```python
from pathlib import Path

Path("report.yaml").write_text(report.to_yaml())   # YAML string
Path("report.json").write_text(report.to_json())   # JSON string
report.print_summary()                             # Console output
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

## The 5 Active Checks (v1.1)

> **Removed in v1.1**: C6 (Sanity Tests) → migrated to MIF Layer 1. C7 (Comprehensive Logging) → replaced by PROD envelope.

### Design Principles

**1. Single Responsibility**
- Each check validates ONE aspect of data quality
- No overlap between checks
- Clear status vocabulary: PASS / FAIL / WARN / SKIP / ERROR

**2. CORE vs ADVISORY Classification**
- **CORE** (C2, C3, C5, PROD): failure → `STATUS_VOID`, `precondition_gate = 0.0`
- **ADVISORY** (C1, C4): warn → `STATUS_WARNING`, gate capped by MPI ≤ 0.8
- Advisory warnings never block certification

**3. Intervention Gravity**
- Each check emits an `InterventionLog` with weighted counts
- `physical_correction` gravity = 1.0 (most severe)
- `forward_fill` gravity = 0.5
- `calendar_removal` gravity = 0.2
- MPI = 100 × (1 − Σ(gravity × count) / N_total_points)

### Check Classification

**CORE — Non-bypassable** (failure → VOID):
| ID | Check | Detects |
|----|-------|---------|
| C2 | IntegrityCheck | H<L, Close∉[L,H], NaN in OHLC, negative volume |
| C3 | CalendarAlignmentCheck | Off-calendar bars; missing calendar in CERT mode |
| C5 | IndexTraceabilityCheck | Duplicates, non-chronological, tz-naive index |
| PROD | Envelope seal | Output trust — always PASS (injected, not a data check) |

**ADVISORY — Configurable** (warn → WARNING):
| ID | Check | Detects |
|----|-------|---------|
| C1 | SourceUniquenessCheck | Single source + metadata (SKIP in Phase 1) |
| C4 | ForwardFillCheck | Consecutive identical values beyond threshold |

### Mode-Specific Behaviour

| Behaviour | CERTIFICATION | DIAGNOSTIC |
|-----------|---------------|------------|
| Calendar | **Required** — FAIL if missing | Optional — auto-detected if absent |
| C3 FAIL on unknown calendar | Yes | No |
| C1 | SKIP (Phase 1) | SKIP (Phase 1) |
| Overall gate on VOID | 0.0 | 0.0 |

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

**Step 2**: Register in DQFValidator before calling `validate()`
```python
config    = DQFConfig(mode=DQFMode.DIAGNOSTIC)
validator = DQFValidator(config)
validator._checks["C_CUSTOM"] = MyCustomCheck()   # add to check dict
report    = validator.validate(df)
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
- C2 (OHLCV Integrity): O(n) comparisons
- C4 (ForwardFill): O(n) rolling window

**Mitigation**:
- All checks use vectorized pandas/numpy operations (no Python loops)
- PRODEnvelope: O(1) — pure dict construction

**Memory Usage**:
- Full DataFrame kept in memory
- MIF-Lite manifest: ~1 KB per validation
- No intermediate copies in Phase 1 (passthrough cleaned_data)

### Optimization Strategies

**Current (v1.1.0)**:
- Vectorized operations (pandas/numpy)
- Sequential execution — 4 active checks
- No I/O in CORE path (C7 removed)

**Future (v1.2.0+)**:
- Optional parallel CORE+ADVISORY execution
- Chunked processing for streaming pipelines

### Scalability

**v1.1.0 Performance**:
- Single-threaded, sequential checks
- Full dataset in memory
- ~0.6s for 100 days (vs ~1.2s in v1.0.0 — C6/C7 removed)

**Target**: 1,000 days in <2 seconds (v1.1.0)  
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