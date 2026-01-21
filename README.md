# DQF - Data Quality Framework

[![Tests](https://img.shields.io/badge/tests-93%20passed-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-92%25-success)](tests/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/symbioticode/mif-dqf)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A standalone framework for validating financial OHLCV data quality before analysis or trading.**

---

## Why DQF Exists

### The Fundamental Problem

**Garbage In, Garbage Out (GIGO)**: No matter how sophisticated your trading algorithms or statistical models, if your input data is corrupted, all results are invalid.

80% of quantitative strategies fail in production not because of flawed logic, but because of **corrupted data during development**.

### The Philosophy of Purification

DQF embodies the principle of **ritual purification** before sacred practice:

- **Islam**: Wuḍū (ablution) - 7 ritual cleansings before Salat (prayer)
- **Shinto**: Temizuya (water purification) before entering a shrine
- **Quantitative Finance**: **DQF** (data purification) before analysis

Without purification, the sacred act (prayer/analysis) is invalid.

### DQF as Layer -1

DQF is the **foundation layer** in the data pipeline:

```
DQF (Layer -1) → Data Quality validation
    ↓
DAL (Layer 0)  → Data Abstraction (multi-source)
    ↓
MIF (Layers 1-5) → Metric Certification
```

**Without clean data, everything built on top is meaningless.**

---

## Overview

DQF (Data Quality Framework) validates financial OHLCV (Open, High, Low, Close, Volume) data through **7 comprehensive checks** before it enters your analysis pipeline.

**Key Characteristics**:
- ✅ **Standalone**: Works independently (no MIF/DAL dependency)
- ✅ **Domain-specific**: Designed for financial time series
- ✅ **Reproducible**: Same data → Same results (always)
- ✅ **Transparent**: Complete provenance tracking

---

## Key Features

### The 7 Checks

| Check | Name | Purpose |
|-------|------|---------|
| 1 | Source Uniqueness | Validates single canonical source + metadata |
| 2 | OHLCV Integrity | Enforces market physics (H≥L, H≥O/C, etc.) |
| 3 | Calendar Alignment | Detects trading calendar, removes weekends/holidays |
| 4 | Forward-Fill Limits | Detects excessive interpolation (data gaps) |
| 5 | Index Traceability | Ensures unique, chronological, timezone-aware index |
| 6 | Sanity Tests | Detects statistical anomalies (returns, volume, volatility) |
| 7 | Comprehensive Logging | Complete provenance tracking + JSON export |

### Core Components

- **DQFValidator**: Orchestrates all 7 checks with robust error handling
- **DQFReport**: Generates consolidated reports (YAML/JSON export)
- **DQFConfig**: YAML-based configuration with validation
- **BaseCheck**: Abstract base class for custom checks

---

## Quick Start

### Installation

**Prerequisites**: Python 3.10+

```bash
# From source
git clone https://github.com/symbioticode/mif-dqf.git
cd mif-dqf
pip install -e .
```

### Minimal Example

```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

# Load your data
data = pd.read_csv("btc_usd.csv", index_col=0, parse_dates=True)

# Default configuration
config = DQFConfig()

# Validate
validator = DQFValidator(config)
report = validator.validate(data)

# Results
print(f"Status: {report.overall_status}")  # PASS or FAIL
print(f"Checks passed: {report.checks_passed}/{report.total_checks}")

# Export report
report.to_yaml("validation_report.yaml")
```

**Expected Output**:
```
Status: PASS
Checks passed: 7/7
Issues detected: 0
Validation complete: validation_report.yaml
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Virtual environment recommended

### From Source

```bash
git clone https://github.com/symbioticode/mif-dqf.git
cd mif-dqf

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install dqf
```

### Verify Installation

```bash
python -c "from dqf import DQFValidator; print('DQF installed successfully')"
```

---

## Basic Usage

### Simple Validation

```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

# Load data
data = pd.read_csv("spy_data.csv", index_col=0, parse_dates=True)

# Validate with defaults
validator = DQFValidator(DQFConfig())
report = validator.validate(data)

# Check results
if report.overall_status == "PASS":
    print("✅ Data is clean and ready for analysis")
    clean_data = report.cleaned_data
else:
    print("❌ Data quality issues detected:")
    for issue in report.all_issues:
        print(f"  - {issue.message}")
```

### Custom Configuration

```python
from dqf import DQFConfig

# Create custom config
config = DQFConfig(
    check_2_integrity={
        'enabled': True,
        'max_violation_rate': 0.005  # Stricter: 0.5% max violations
    },
    check_4_ffill={
        'enabled': True,
        'max_consecutive': 1,  # Maximum 1 day forward-fill
        'severity': 'CRITICAL'
    },
    output={
        'log_dir': 'logs',
        'report_dir': 'reports'
    }
)

# Validate
validator = DQFValidator(config)
report = validator.validate(data)
```

### YAML Configuration

```yaml
# config.yaml
dqf_version: "1.0.0"

checks:
  check_1_source:
    enabled: true
    require_metadata: true
  
  check_2_integrity:
    enabled: true
    max_violation_rate: 0.01
  
  check_3_calendar:
    enabled: true
    auto_detect: true
  
  check_4_ffill:
    enabled: true
    max_consecutive: 3
    severity: "WARNING"

output:
  log_dir: "logs"
  report_dir: "reports"
```

```python
# Load config from YAML
config = DQFConfig.from_yaml("config.yaml")
validator = DQFValidator(config)
report = validator.validate(data)
```

### Accessing Results

```python
# Overall status
print(f"Status: {report.overall_status}")  # PASS or FAIL

# Individual check results
for check_name, result in report.check_results.items():
    print(f"{check_name}: {result.status}")

# Issues
if report.all_issues:
    print(f"Found {len(report.all_issues)} issues:")
    for issue in report.all_issues:
        print(f"  [{issue.severity}] {issue.message}")

# Cleaned data (if PASS)
if report.overall_status == "PASS":
    clean_data = report.cleaned_data
    clean_data.to_csv("clean_data.csv")

# Export report
report.to_yaml("report.yaml")
report.to_json("report.json")
```

---

## Documentation

### Core Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Design philosophy, component diagram, technical decisions
- **[API Reference](docs/API.md)** - Complete API documentation with examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Examples

- **[examples/01_basic_validation.py](examples/)** - Simple validation workflow
- **[examples/02_custom_config.py](examples/)** - Advanced configuration
- **[examples/03_batch_processing.py](examples/)** - Multi-file validation

### Additional Resources

- **[DQF_PROJECT.md](DQF_PROJECT.md)** - Project history, evolution, roadmap
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

---

## Project Status

**Version**: 1.0.0 (Production Ready)  
**Release Date**: January 12, 2026  
**Status**: ✅ Stable

### Metrics

- **Tests**: 93 (84 unit + 9 integration)
- **Coverage**: 92%+
- **Code Quality**: Zero lint warnings (ruff + black)
- **Type Safety**: 100% type hints (mypy compatible)

### Roadmap

**v1.1.0** (Q1 2026) - Optimization & Polish
- Performance optimization for large datasets
- Additional examples and tutorials
- Enhanced documentation

**v1.2.0** (Q1 2026) - Active Data Cleaning
- Optional auto-cleaning mode
- Configurable cleaning strategies
- Before/after diff reports

**v2.0.0** (Q2 2026) - DAL Integration
- Integration with Data Abstraction Layer
- Enhanced provenance tracking
- MIF compatibility layer

---

## Contributing

We welcome contributions! DQF follows strict quality standards:

### Standards

- ✅ **Tests**: All new features require tests (coverage >90%)
- ✅ **Type Hints**: Complete type annotations
- ✅ **Documentation**: Docstrings for all public APIs
- ✅ **Code Quality**: Pass ruff + black linting
- ✅ **Commit Messages**: [Conventional Commits](https://www.conventionalcommits.org/)

### Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-check`)
3. Write tests first (TDD encouraged)
4. Implement feature
5. Ensure all tests pass (`pytest`)
6. Ensure lint clean (`ruff check . && black --check .`)
7. Commit changes (`git commit -m 'feat: add amazing check'`)
8. Push to branch (`git push origin feature/amazing-check`)
9. Open Pull Request

### Adding Custom Checks

See [examples/custom_check_example.py](examples/) for a complete guide on creating custom checks by inheriting from `BaseCheck`.

---

## License

MIT License (to be added upon GitHub publication)

---

## Authors

- **dravitch** - Lead Developer
- **Claude (Anthropic)** - Architecture & Implementation Assistant
- **Grok (xAI)** - Workflow Supervision & Quality Assurance

---

## Acknowledgments

- **NixOS Community** - Reproducible development environment
- **MIF Project** - Inspiration for methodological rigor
- **pandas & pytest** - Excellent foundational tools

---

## Support

- **Issues**: [GitHub Issues](https://github.com/symbioticode/mif-dqf/issues)
- **Discussions**: [GitHub Discussions](https://github.com/symbioticode/mif-dqf/discussions)
- **Documentation**: [Full Docs](docs/)

---

**�
