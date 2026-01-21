#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Bootstrap DQF v4.8 (NixOS Edition)"

PROJECT_NAME="dqf"

# 1. Utiliser init_project.py existant
echo "📦 Initializing reproducible environment..."
python ../init_project.py "$PROJECT_NAME"

cd "$PROJECT_NAME"

# 2. Créer structure DQF spécifique
echo "🏗️  Creating DQF structure..."

# Directories
mkdir -p dqf/{core,checks,utils,config}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p examples
mkdir -p docs
mkdir -p scripts
mkdir -p _work/dqf/{logs,provenance,reports}

# __init__.py files
touch dqf/__init__.py
touch dqf/core/__init__.py
touch dqf/checks/__init__.py
touch dqf/utils/__init__.py
touch tests/__init__.py

# Placeholder files pour structure
touch dqf/core/validator.py
touch dqf/core/report.py
touch dqf/core/config.py
touch dqf/checks/base.py

# Config templates
cat > dqf/config/default_config.yaml << 'EOF'
# DQF Configuration v4.8
dqf_version: "4.8"

# Check 1: Source Uniqueness
source_uniqueness:
  enabled: true
  require_metadata: true

# Check 2: OHLCV Integrity
ohlcv_integrity:
  enabled: true
  max_violation_rate: 0.01

# Check 3: Calendar Alignment
calendar_alignment:
  enabled: true
  auto_detect: true
  default_calendar: "NYSE"

# Check 4: Forward-Fill Limits
forward_fill_limits:
  enabled: true
  max_consecutive_ffill: 3
  warn_threshold: 2

# Check 5: Index Traceability
index_traceability:
  enabled: true
  require_unique: true

# Check 6: Sanity Tests
sanity_tests:
  enabled: true
  extreme_return:
    threshold: 1.0
  zero_volume:
    max_consecutive_days: 5

# Check 7: Comprehensive Logging
comprehensive_logging:
  enabled: true
  log_level: "INFO"
  save_provenance: true

# Output paths
output:
  log_dir: "_work/dqf/logs"
  provenance_dir: "_work/dqf/provenance"
  report_dir: "_work/dqf/reports"
EOF

cat > dqf/config/calendars.yaml << 'EOF'
# Trading Calendars Configuration

calendars:
  NYSE:
    description: "New York Stock Exchange"
    trading_days: "Mon-Fri"
    remove_weekends: true
    remove_holidays: true
    timezone: "America/New_York"
    
  CRYPTO_24_7:
    description: "24/7 Cryptocurrency Markets"
    trading_days: "All"
    remove_weekends: false
    remove_holidays: false
    timezone: "UTC"
    
  FOREX_24_5:
    description: "Forex Markets (24h Mon-Fri)"
    trading_days: "Mon-Fri"
    remove_weekends: true
    remove_holidays: false
    timezone: "UTC"
EOF

# 3. Adapter pyproject.toml pour DQF
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dqf"
version = "4.8.0"
description = "Data Quality Framework for Financial Time Series"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}

dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0",
    "python-dateutil>=2.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

calendar = [
    "pandas-market-calendars>=4.3.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = [
    "-v",
    "--tb=short",
    "--cov=dqf",
    "--cov-report=term-missing",
]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"
EOF

# 4. README principal
cat > README.md << 'EOF'
# DQF - Data Quality Framework v4.8

**Framework de validation qualité pour données financières**

## 🎯 Quick Start
```python
from dqf import DQFValidator
import pandas as pd

df = pd.read_csv('data.csv', index_col='date', parse_dates=True)
validator = DQFValidator()
report = validator.validate(df, symbol='BTC-USD', source='yahoo')

if report.is_clean():
    print("✅ Data is CLEAN")
else:
    print(f"❌ {report.failed_count}/7 checks FAILED")
```

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [7 Checks Explained](docs/checks_explained.md)
- [API Reference](docs/api_reference.md)

## �� Development
```bash
# Linter
just lint

# Tests
just test

# Format
just format
```
EOF

# 5. Justfile adapté DQF
cat > justfile << 'EOF'
default: lint test

# Lint code
lint:
    ruff check dqf tests examples
    black --check dqf tests examples

# Format code
format:
    black dqf tests examples
    ruff --fix dqf tests examples

# Run tests
test:
    pytest -v

# Run tests with coverage
test-cov:
    pytest -v --cov=dqf --cov-report=html

# Clean cache
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf htmlcov
    rm -rf _work/*
    find . -type d -name __pycache__ -exec rm -rf {} +

# Sync changes to git
sync MESSAGE:
    git add .
    git commit -m "{{MESSAGE}}" || echo "Nothing to commit"
    git pull --rebase
    git push

# Install dev dependencies
install-dev:
    pip install -e ".[dev]"
EOF

# 6. Créer placeholder examples
cat > examples/01_basic_validation.py << 'EOF'
"""
Example 1: Basic DQF Validation

Shows simplest usage of DQF validator.
"""

import pandas as pd
from dqf import DQFValidator

def main():
    # Load data
    df = pd.read_csv('tests/fixtures/clean_data.csv', 
                     index_col='date', 
                     parse_dates=True)
    
    # Validate
    validator = DQFValidator()
    report = validator.validate(df, symbol='BTC-USD', source='test_fixture')
    
    # Results
    print(report.summary())
    
    if report.is_clean():
        clean_df = report.get_cleaned_data()
        print(f"\n✅ {len(clean_df)} clean data points ready")
    else:
        print(f"\n❌ Validation failed: {report.failed_count}/7 checks")

if __name__ == "__main__":
    main()
EOF

# 7. Commit structure
git add .
git commit -m "chore: Bootstrap DQF v4.8 structure (NixOS)

- Created DQF package structure
- Added config templates (default_config.yaml, calendars.yaml)
- Added justfile with lint/test/format commands
- Added example scripts
- Configured pyproject.toml for DQF
"

echo ""
echo "✅ DQF v4.8 structure bootstrapped"
echo ""
echo "📋 Next steps:"
echo "   1. direnv allow"
echo "   2. pip install -e \".[dev]\""
echo "   3. git checkout -b feature/check-1-source"
echo "   4. Start implementing Check 1 (Source Uniqueness)"
echo ""
echo "🔍 Verify setup:"
echo "   just lint    # Should pass (no code yet)"
echo "   just test    # Should pass (no tests yet)"
