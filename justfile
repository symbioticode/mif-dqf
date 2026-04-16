# Justfile — DQF
# Usage: just <command>  |  just --list

default: sanitize

# ─────────────────────────────────────────────
# CODE QUALITY
# ─────────────────────────────────────────────

# Format code (black + isort)
format:
    black dqf tests examples
    isort dqf tests examples

# Lint (ruff + black check)
lint:
    ruff check dqf tests examples
    black --check dqf tests examples

# Auto-fix linting issues, then verify
fix:
    ruff check --fix dqf tests examples
    isort dqf tests examples
    black dqf tests examples

# Fix encoding issues
fix-encoding:
    python scripts/dqf_tools.py fix-encoding

# Full quality pipeline: fix → lint → test
sanitize: fix lint test

# ─────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────

# Run all tests
test:
    pytest tests/ -v

# Run tests with coverage report
test-cov:
    pytest tests/ -v --cov=dqf --cov-report=term-missing --cov-report=html

# Run unit tests only
test-unit:
    pytest tests/unit/ -v

# Run integration tests only
test-integration:
    pytest tests/integration/ -v

# Run tests matching a pattern
test-match PATTERN:
    pytest tests/ -v -k "{{PATTERN}}"

# ─────────────────────────────────────────────
# BASELINE
# ─────────────────────────────────────────────

# Minimal baseline (3 checks: imports, linting, tests) — used in CI
baseline:
    python scripts/baseline.py

# Full validation (5 checks: tests, examples, linting, build, coherence)
# Requires scripts/local/validate.py  →  git show ac5c04d:scripts/test_baseline_v1.0.0.py > scripts/local/validate.py
validate:
    @test -f scripts/local/validate.py || (echo "❌ scripts/local/validate.py not found — see justfile comment" && exit 1)
    python scripts/local/validate.py

# Full validation, skipping slow build step
validate-fast:
    @test -f scripts/local/validate.py || (echo "❌ scripts/local/validate.py not found" && exit 1)
    python scripts/local/validate.py --no-build

# ─────────────────────────────────────────────
# EXAMPLES
# ─────────────────────────────────────────────

# Run all 4 examples
run-examples:
    python examples/01_basic_validation.py
    python examples/02_custom_config.py
    python examples/03_batch_processing.py
    python examples/04_custom_check.py

# Run specific example by number (just example 1)
example NUM:
    python examples/0{{NUM}}_*.py

# ─────────────────────────────────────────────
# PACKAGE
# ─────────────────────────────────────────────

# Install in editable mode with dev dependencies
install-dev:
    pip install -e ".[dev]"

# Build wheel + sdist
build:
    rm -rf build/ dist/ *.egg-info
    python -m build
    ls -lh dist/

# Verify package with twine
check-package:
    twine check dist/*

# Publish to TestPyPI (safe test)
publish-test:
    twine upload --repository testpypi dist/*

# Publish to PyPI (production — requires confirmation)
publish:
    @echo "⚠️  Publishing to PyPI (production). Press Enter to confirm, Ctrl+C to abort."
    @read _confirm
    twine upload dist/*

# Full release workflow: clean → validate → build → check
release VERSION:
    @echo "Preparing release {{VERSION}}..."
    @just clean
    @just sanitize
    @just build
    @just check-package
    @echo ""
    @echo "✅ Release {{VERSION}} ready. Next: just publish-test → just publish"

# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────

# Remove Python artifacts and build files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache htmlcov .coverage build/ dist/

# Personal backup + cleanup  (requires scripts/local/cleanup.sh)
backup:
    @test -f scripts/local/cleanup.sh || (echo "❌ scripts/local/cleanup.sh not found — personal script, not in repo" && exit 1)
    bash scripts/local/cleanup.sh

# Restore from personal backup  (requires scripts/local/cleanup.sh)
restore:
    @test -f scripts/local/cleanup.sh || (echo "❌ scripts/local/cleanup.sh not found" && exit 1)
    bash scripts/local/cleanup.sh restore

# ─────────────────────────────────────────────
# GIT
# ─────────────────────────────────────────────

# Git sync (commit + push)
sync MESSAGE:
    @echo " Git sync..."
    python scripts/local/sync.py "{{MESSAGE}}"
    @echo " Sync complete"

# Annotated tag + push
tag VERSION MESSAGE:
    git tag -a {{VERSION}} -m "{{MESSAGE}}"
    git push origin {{VERSION}}
    @echo " Tag {{VERSION}} created"


# ─────────────────────────────────────────────
# DIAGNOSTICS
# ─────────────────────────────────────────────

# Check non-ASCII characters
check-encoding:
    python scripts/dqf_tools.py check-encoding

# Run environment doctor
doctor:
    python scripts/dqf_tools.py doctor

# Project statistics
stats:
    @echo "Production code:"
    @find dqf -name "*.py" ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1
    @echo "Test code:"
    @find tests -name "*.py" ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1
    @echo "Git commits:"
    @git log --oneline | wc -l

# ─────────────────────────────────────────────
# NixOS (local only)
# ─────────────────────────────────────────────

# Enter Nix dev shell
nix-dev:
    nix develop
