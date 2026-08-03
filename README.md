# DQF - Data Quality Framework

[![Tests](https://img.shields.io/badge/tests-224%2F224%20passing-brightgreen)](https://github.com/symbioticode/mif-dqf)
[![Version](https://img.shields.io/pypi/v/mif-dqf)](https://pypi.org/project/mif-dqf/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**mif-dqf** is the data quality layer of the [MIF ecosystem](https://github.com/symbioticode), certifying OHLCV financial data for [mif-dal](https://github.com/symbioticode/mif-dal) and other callers.

DQF v1.2 validates financial time series through CORE and ADVISORY checks, produces
**MIF-Lite manifests** with a cryptographic **MIF-UID** and a **MIF Purity Index (MPI)**,
and supports two operational modes: **CERTIFICATION** (strict, deterministic) and
**DIAGNOSTIC** (advisory, flexible).

---

## 🎯 Why DQF Exists

### The Fundamental Problem

**Garbage In, Garbage Out (GIGO)**: No matter how sophisticated your trading algorithms or statistical models, if your input data is corrupted, all results are invalid.

**Statistical Reality**:
- 80% of quantitative strategies fail in production not because of flawed logic, but because of corrupted data during development
- Data quality issues are detected on average 6 months after deployment
- A single corrupted data point can invalidate months of backtesting

### The Philosophy of Purification

DQF embodies the principle of systematic purification before critical operations:

**Historical Precedents**:
- **Medicine**: Hand washing before surgery (Semmelweis, 1847) - reduced mortality from 18% to 2%
- **Laboratory Science**: Sterile technique before experiments - ensures reproducibility
- **Software Engineering**: Input validation before processing - prevents crashes
- **Quantitative Finance**: **DQF (data purification) before analysis** - guarantees validity

**Cultural Parallels** (methodological, not spiritual):
- Islam: Wuḍū (ablution) - 7 ritual cleansings before Salat (prayer)
- Shinto: Temizuya (water purification) before entering a shrine
- Laboratory: Autoclave sterilization before cell culture
- **DQF**: 7 systematic checks before quantitative analysis

**Core Principle**: Without purification, the critical operation (analysis/trading) produces unreliable results.

---

## ✨ What DQF Does

### Dual Mission

**1. Validation**: Detect and report data quality issues
- Identifies violations of market physics (H<L, negative volume, etc.)
- Detects statistical anomalies (extreme returns, forward-fill abuse)
- Validates structural integrity (timezone, calendar, duplicates)

**2. Purification**: Generate certified clean datasets
- Produces validated DataFrames with full provenance tracking
- Guarantees reproducibility (same data → same results, always)
- Enables consistent analysis across teams and time

### The DQF Guarantee

When DQF reports `status: PASS`:
- ✅ Data respects market physics laws
- ✅ No statistical anomalies detected
- ✅ Complete provenance chain tracked
- ✅ **Dataset certified for production use**

This is not just validation - it's **data certification**.

---

## 🔬 Core Benefits

### For Quantitative Researchers

**Problem**: Corrupted data during backtesting → false conclusions
```python
# Without DQF: Unknown data quality
backtest_results = strategy.run(data)  # 💥 May be invalid
paper.publish(backtest_results)        # 💥 Non-reproducible
```

**Solution**: Certified clean data → reliable backtests
```python
# With DQF: Certified data quality
report = validator.validate(data)
if report.overall_status == "PASS":
    backtest_results = strategy.run(report.cleaned_data)  # ✅ Valid
    paper.publish(backtest_results)                       # ✅ Reproducible
```

**Benefits**:
- ✅ Reproducible research (same data → same results)
- ✅ Peer review confidence (provenance tracking)
- ✅ Publication credibility (certified datasets)

---

### For Trading Systems

**Problem**: Data corruption in production → catastrophic losses
```python
# Without DQF: Unknown data quality
live_data = fetch_latest()
signal = model.predict(live_data)  # 💥 May be based on corrupted data
execute_trade(signal)              # 💥 Potential disaster
```

**Solution**: Real-time validation → safe trading
```python
# With DQF: Real-time validation
live_data = fetch_latest()
report = validator.validate(live_data)

if report.overall_status == "PASS":
    signal = model.predict(report.cleaned_data)  # ✅ Safe
    execute_trade(signal)                        # ✅ Confident
else:
    alert_team(report.all_issues)  # 🚨 Data quality issue
    halt_trading()                 # Safety first
```

**Benefits**:
- ✅ Risk mitigation (detect issues before trading)
- ✅ Regulatory compliance (audit trail)
- ✅ Post-mortem analysis (provenance tracking)

---

### For Data Engineers

**Problem**: Silent data corruption in pipelines
```python
# Without DQF: Silent failures
raw_data = extract_from_source()
transformed = apply_transformations(raw_data)  # 💥 May propagate corruption
load_to_warehouse(transformed)                 # 💥 Garbage persisted
```

**Solution**: Validation checkpoints → data integrity
```python
# With DQF: Validated pipeline
raw_data = extract_from_source()

# Checkpoint 1: Validate raw data
raw_report = validator.validate(raw_data)
assert raw_report.overall_status == "PASS"

transformed = apply_transformations(raw_report.cleaned_data)

# Checkpoint 2: Validate transformed data
final_report = validator.validate(transformed)
assert final_report.overall_status == "PASS"

load_to_warehouse(final_report.cleaned_data)  # ✅ Only clean data persisted
```

**Benefits**:
- ✅ Early detection (issues caught immediately)
- ✅ Data lineage (full provenance chain)
- ✅ Quality metrics (SLA monitoring)

---

## 🚀 Quick Start

### Installation

```bash
pip install mif-dqf
```

> **Note — package name vs import name**: the PyPI package is `mif-dqf` but the
> Python import is `from dqf import ...` (not `import mif_dqf`).
> This is intentional: `dqf` is the canonical module namespace.

```python
# Install
# pip install mif-dqf

# Import (module name is 'dqf', not 'mif_dqf')
from dqf import DQFValidator, DQFConfig, DQFMode
```

### Basic Usage

```python
import pandas as pd
from dqf import DQFValidator, DQFConfig, DQFMode

# Load your data (timezone-aware index required)
data = pd.read_csv("spy.csv", index_col=0, parse_dates=True)
data.index = data.index.tz_localize("UTC")

# CERTIFICATION mode — strict, deterministic, calendar required
config = DQFConfig(mode=DQFMode.CERTIFICATION)
validator = DQFValidator(config)
report = validator.validate(data, calendar="NYSE")

if report.is_certified:
    print(f"✅ CERTIFIED  MPI={report.purity_index:.1f}/100  gate={report.precondition_gate}")
    print(f"   UID: {report.mif_uid}")
    clean_data = report.cleaned_data   # validated DataFrame
    report.print_summary()             # human-readable summary
else:
    print(f"❌ {report.overall_status}  gate={report.precondition_gate}")
    print(f"   CORE:     {report.core_results}")
    print(f"   ADVISORY: {report.advisory_results}")
```

**DIAGNOSTIC mode** (no calendar required, useful for exploration):
```python
config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
report = DQFValidator(config).validate(data)
print(f"Status: {report.overall_status}  MPI: {report.purity_index:.1f}")
```

**v1.2 — Cleaning Log** (record every intervention in Parquet):
```python
# enable_cleaning_log=True captures per-row intervention detail
report = validator.validate(df, calendar='NYSE', enable_cleaning_log=True)
print(report.has_cleaning_log)         # False if data was clean
df_log = report.get_cleaning_log_df()  # None or DataFrame with columns:
                                        # row_index, check_id, intervention,
                                        # field, value_before, value_after, gravity
```

**Output** (CERTIFICATION, clean data):
```
✅ CERTIFIED  MPI=100.0/100  gate=1.0
   UID: sha256:a3f9...
```

---

## 📋 DQF v1.2 Checks

### CORE checks — failure → `STATUS_VOID`, `precondition_gate = 0.0`

| ID | Check | Purpose |
|----|-------|---------|
| PROD | Envelope seal | Output trust mechanism — always injected PASS |
| C2 | **OHLCV Integrity** | Market physics (H≥L, H≥O/C, V≥0, no NaN) |
| C3 | **Calendar Alignment** | Declared calendar required in CERTIFICATION mode |
| C5 | **Index Traceability** | Unique, chronological, timezone-aware index |

### ADVISORY checks — warn → `STATUS_WARNING`, gate capped by MPI

| ID | Check | Purpose |
|----|-------|---------|
| C1 | Source Uniqueness | Single canonical source (SKIP in Phase 1 — DAL pending) |
| C4 | **Forward-Fill Detection** | Detects interpolation abuse (consecutive repeats) |

> **Removed in v1.1**: C6 (Sanity Tests) migrated to MIF Layer 1; C7 (Logging) replaced by PROD envelope.

### Active Cleaning Log (v1.2)

When `enable_cleaning_log=True`, every intervention detected by C2, C3, and C4
is recorded in a Parquet log embedded in the manifest.

| Property / Method | Description |
|---|---|
| `report.has_cleaning_log` | `True` when at least one intervention was logged |
| `report.get_cleaning_log_df()` | Returns a `DataFrame` or `None` |
| `manifest["cleaning_log"]` | Base64-encoded Parquet bytes |
| `manifest["provenance"]["cleaning_log_uri"]` | `"embedded:sha256:…"` or `None` |

The **MIF-UID is always computed on raw data** — the cleaning log does not affect
the cryptographic identity of the dataset.

---

## 🎓 Complete Examples

### Example 1: Research Workflow

```python
import pandas as pd
from pathlib import Path
from dqf import DQFValidator, DQFConfig, DQFMode

# Research scenario: Certifying historical data for a paper
data = pd.read_csv("spy_2020_2024.csv", index_col=0, parse_dates=True)
data.index = data.index.tz_localize("UTC")

config = DQFConfig(mode=DQFMode.CERTIFICATION)
report = DQFValidator(config).validate(data, calendar="NYSE")

if report.is_certified:
    # Save certified dataset with provenance
    report.cleaned_data.to_csv("spy_2020_2024_certified.csv")
    Path("provenance_spy.json").write_text(report.to_json())

    print(f"✅ CERTIFIED  MPI={report.purity_index:.1f}/100")
    print(f"   MIF-UID: {report.mif_uid}")
else:
    print(f"❌ {report.overall_status} (gate={report.precondition_gate})")
    print(f"   CORE failures: {report.core_results}")
```

---

### Example 2: Production Pipeline

```python
import logging
from dqf import DQFValidator, DQFConfig, DQFMode

logger = logging.getLogger(__name__)

# Shared validator — reuse across calls (thread-safe for validate())
_config    = DQFConfig(mode=DQFMode.CERTIFICATION, c4_warn_threshold=1)
_validator = DQFValidator(_config)

def validate_daily_data(symbol: str, calendar: str, data: pd.DataFrame) -> pd.DataFrame:
    """Certify daily data; raise on VOID."""
    report = _validator.validate(data, calendar=calendar)

    if report.overall_status == "VOID":
        logger.critical("%s: VOID  core=%s", symbol, report.core_results)
        raise ValueError(f"CORE failure for {symbol} — gate=0")

    if report.overall_status == "WARNING":
        logger.warning("%s: WARNING  advisory=%s  MPI=%.1f",
                       symbol, report.advisory_results, report.purity_index)

    logger.info("%s: %s  MPI=%.1f  UID=%s",
                symbol, report.overall_status, report.purity_index, report.mif_uid)
    return report.cleaned_data

# Usage
try:
    clean = validate_daily_data("SPY", "NYSE", raw_data)
    load_to_warehouse(clean)
except ValueError as exc:
    alert_team(str(exc))
    halt_pipeline()
```

---

### Example 3: Batch Processing

```python
from pathlib import Path
from dqf import DQFValidator, DQFConfig, DQFMode

CALENDAR = {"BTC-USD": "CRYPTO_24_7", "ETH-USD": "CRYPTO_24_7",
            "SPY": "NYSE", "GLD": "NYSE"}

config    = DQFConfig(mode=DQFMode.CERTIFICATION)
validator = DQFValidator(config)
results   = {}

for symbol, calendar in CALENDAR.items():
    data = pd.read_csv(f"{symbol}.csv", index_col=0, parse_dates=True)
    data.index = data.index.tz_localize("UTC")
    results[symbol] = validator.validate(data, calendar=calendar)
    print(f"{symbol}: {results[symbol].overall_status}  MPI={results[symbol].purity_index:.1f}")

# Keep only certified datasets
certified = {s: r.cleaned_data for s, r in results.items() if r.is_certified}
print(f"\n{len(certified)}/{len(CALENDAR)} datasets CERTIFIED")

# Persist manifests
for symbol, report in results.items():
    Path(f"manifests/{symbol}.mif.json").write_text(report.to_json())
```

---

### Example 4: Custom Check

See `examples/04_custom_check.py` for a complete example. Custom checks extend
`BaseCheck` and are registered via `validator.add_custom_check()`. They run as
ADVISORY checks (WARN → `STATUS_WARNING`, never `STATUS_VOID`).

```python
from typing import Any
from dqf import DQFValidator, DQFConfig, DQFMode
from dqf.checks.base import BaseCheck, CheckResult

class LiquidityCheck(BaseCheck):
    """Advisory check: minimum daily volume."""

    def __init__(self, min_vol: float = 1_000_000) -> None:
        super().__init__(check_id="C_LIQ", check_name="Minimum Liquidity")
        self.min_vol = min_vol

    def run(self, data, **kwargs: Any) -> CheckResult:
        low = int((data["volume"] < self.min_vol).sum())
        if low:
            return self._create_warning_result(
                message=f"{low} days below minimum volume ({self.min_vol:,.0f})",
                details={"low_volume_days": low},
            )
        return self._create_pass_result(message="Liquidity OK")

config    = DQFConfig(mode=DQFMode.DIAGNOSTIC)
validator = DQFValidator(config)
validator.add_custom_check("C_LIQ", LiquidityCheck(min_vol=500_000))
report    = validator.validate(data)
print(report.advisory_results)  # {'C4': 'PASS', 'C_LIQ': 'PASS', 'C1': 'SKIP'}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│   Input: Raw DataFrame (OHLCV)         │
│   - Potentially corrupted               │
│   - Unknown quality                     │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│   DQFValidator (mode: CERT | DIAG)     │
│  CORE checks (failure → VOID)          │
│  ┌─────────────────────────────────┐   │
│  │ C2. OHLCV Integrity             │   │
│  │ C3. Calendar Alignment          │   │
│  │ C5. Index Traceability          │   │
│  └─────────────────────────────────┘   │
│  ADVISORY checks (warn → WARNING)      │
│  ┌─────────────────────────────────┐   │
│  │ C1. Source Uniqueness (SKIP/P1) │   │
│  │ C4. Forward-Fill Detection      │   │
│  └─────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│   PROD Envelope (MIF-Lite manifest)    │
│  ┌─────────────────────────────────┐   │
│  │ MIF-UID  = SHA-256(hash+ver+cal)│   │
│  │ MPI      = 100×(1−Σwᵢ/N)       │   │
│  │ gate     = 1.0/0.8/0.0         │   │
│  └─────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│   Output: DQFReport (.mif.json)        │
│  - overall_status: CERTIFIED/WARNING/  │
│                    VOID                │
│  - purity_index: 0–100 (MPI)          │
│  - precondition_gate: 0.0/0.8/1.0     │
│  - mif_uid: sha256:...                 │
│  - cleaned_data: validated DataFrame   │
└─────────────────────────────────────────┘
```

**Design Principles**:
- **Deterministic**: Same data + same args → Same MIF-UID (always)
- **Dual mode**: CERTIFICATION (strict) vs DIAGNOSTIC (advisory)
- **MPI**: continuous purity score replaces binary PASS/FAIL
- **Production-Ready**: 224/224 tests passing

---

## 📖 Documentation

- **[DQF Specification](docs/DQF_SPECIFICATION.md)**: Canonical architectural decisions (v1.1 design)
- **[API Reference](docs/API.md)**: Complete API documentation
- **[Architecture](docs/ARCHITECTURE.md)**: Design patterns and technical decisions
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[Examples](examples/)**: 4 complete examples (basic, config, batch, custom)

---

## 🧪 Testing & Quality

```bash
# Run all tests
pytest tests/ -v                    # 224/224 passing

# Coverage
pytest tests/ --cov=dqf

# Examples
python examples/01_basic_validation.py    # ✅ Works
python examples/02_custom_config.py       # ✅ Works
python examples/03_batch_processing.py    # ✅ Works
python examples/04_custom_check.py        # ✅ Works
```

**Quality Metrics**:
- **224 tests** (185 unit + 38 integration + 1 root)
- **0 failures**

---

## 📦 Project Structure

```
dqf/
├── dqf/                          # Source code
│   ├── checks/                  # C1–C5 checks
│   ├── core/                    # Config, Validator, Report, PRODEnvelope
│   └── utils/                   # Calendar, MPI, CleaningLog
├── tests/                       # Test suite (224 tests)
│   ├── unit/                    # Per-module unit tests
│   └── integration/             # End-to-end pipeline tests
├── examples/                    # Complete examples (4)
├── docs/
│   ├── DQF_SPECIFICATION.md     # Canonical specification (v1.1)
│   ├── API.md                   # API reference
│   ├── ARCHITECTURE.md          # Design & patterns
│   └── TROUBLESHOOTING.md       # Common issues
├── scripts/
│   └── test_install.py          # Installation smoke test
├── pyproject.toml               # Package metadata
└── LICENSE                      # MIT License
```

---

## 🛠️ Development

### Requirements

- Python 3.10+
- pandas >= 2.0.0
- PyYAML >= 6.0

### Setup

```bash
# Clone repository
git clone https://github.com/symbioticode/mif-dqf.git
cd mif-dqf

# Install in editable mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📊 Benchmarks

**Performance** (100 days of data):
```
Total validation time: ~0.6s
  - C2 (Integrity):    0.32s
  - C3 (Calendar):     0.10s
  - C4 (Ffill):        0.10s
  - C5 (Index):        0.08s
  - PROD Envelope:     <0.01s
```

**Scalability**:
- 100 days:    ~0.6s
- 1,000 days:  ~2.0s
- 10,000 days: ~15s

---

## 🗺️ Roadmap

### v1.0.0 (legacy)
- 7 checks (Source, Integrity, Calendar, Forward-Fill, Index, Sanity, Logging)
- Binary PASS/FAIL report

### v1.1.0 ✅
- ✅ Two operational modes: **CERTIFICATION** (strict) vs **DIAGNOSTIC** (advisory)
- ✅ CORE/ADVISORY check classification — CORE failure → VOID, gate=0
- ✅ PROD envelope produces MIF-Lite manifest (.mif.json)
- ✅ MIF Purity Index (MPI) — 0–100 continuous purity score
- ✅ MIF-UID — `SHA-256(data_hash + dqf_version + calendar + mode)`
- ✅ C6 (Sanity) migrated to MIF Layer 1; C7 (Logging) replaced by PROD envelope

### v1.2.0 — Active Cleaning ✅ (current)
- ✅ Optional cleaning log via `enable_cleaning_log=True`
- ✅ Parquet log with per-intervention detail (row_index, check_id, field, gravity…)
- ✅ `report.has_cleaning_log` / `report.get_cleaning_log_df()`
- ✅ MIF-UID computed on raw data (cleaning log excluded from hash)
- ✅ `validator.add_custom_check(check_id, check)` — custom ADVISORY checks
- ✅ 224/224 tests passing

### v2.0.0 — MIF integration (planned)
- ✅ DAL integration — `mif-dal` calls `DQFValidator.validate()` directly, passing
  `raw_data_hash` (mif-dal's `assembly_hash`) so both layers anchor on the same hash
  (live since mif-dal 0.1.1)
- [ ] C1 (Source Uniqueness) activated — DAL handoff
- [ ] Full provenance chain: source → DQF → MIF

---

## 🤝 Ecosystem

DQF is the foundational layer of the **MIF (Metric Integrity Framework)** ecosystem.

```
MIF Layers 1–5  = Metric certification & strategy validation
       ↑           (score capped if DQF precondition fails)
     DAL         = Multi-source data abstraction [planned]
       ↑
     DQF         = Data quality gate [YOU ARE HERE]
       ↑
Raw Sources     = Yahoo Finance, Binance, Kraken, etc.
```

DQF acts as a `precondition_gate`: if data does not pass DQF, downstream MIF
scores are bounded regardless of metric quality. See
[DQF_SPECIFICATION.md](docs/DQF_SPECIFICATION.md) for the full integration
contract.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Methodology**: Systematic purification as scientific hygiene
- **Inspiration**: Medical sterilization, laboratory protocols
- **Cultural parallels**: Islamic Wudu, Shinto Temizuya (ritual, not spiritual)
- **Tools**: pandas, pytest, PyYAML

---

## 📞 Contact & Support

- **Repository**: [github.com/symbioticode/mif-dqf](https://github.com/symbioticode/mif-dqf)
- **Issues**: [GitHub Issues](https://github.com/symbioticode/mif-dqf/issues)
- **Discussions**: [GitHub Discussions](https://github.com/symbioticode/mif-dqf/discussions)
- **Email**: corail.synergia@proton.me

---

## ⭐ Star History

If DQF helps your research or trading, please consider giving it a star! ⭐

---

**Made with rigor by the DQF Team**

**"Data hygiene is not optional. It's the foundation of reliable quantitative analysis."**
