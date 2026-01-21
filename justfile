# Justfile for DQF project
# Usage: just <command>

default: sanitize

# === CODE QUALITY ===

# Format code with black
format:
    @echo " Formatting..."
    black dqf tests examples || true
    isort dqf tests examples || true
    @echo " Formatting complete"

# Lint code
lint:
    @echo " Linting..."
    ruff check dqf tests examples
    black --check dqf tests examples
    mypy dqf || true
    @echo " Linting OK"

# Auto-fix linting issues
fix:
    @echo " Auto-fix..."
    ruff check --fix dqf tests examples
    isort dqf tests examples
    black dqf tests examples
    @echo " Auto-fix complete"

# All in one code quality check
sanitize:
    @echo " SANITIZE..."
    @python scripts/dqf_tools.py fix-encoding || true
    @python scripts/dqf_tools.py check-encoding || true
    @just format
    @just lint
    @just test
    @echo " SANITIZE COMPLETE"

# === TESTING ===

# Run all tests
test:
    @echo " Tests..."
    pytest tests/ -v

# Run tests with coverage
test-cov:
    @echo " Tests with coverage..."
    pytest tests/ -v --cov=dqf --cov-report=term-missing --cov-report=html

# Run specific test file
test-file FILE:
    @echo " Testing {{FILE}}..."
    pytest {{FILE}} -v

# Run tests matching pattern
test-match PATTERN:
    @echo " Testing pattern: {{PATTERN}}..."
    pytest tests/ -v -k "{{PATTERN}}"

# Run integration tests only
test-integration:
    @echo " Integration tests..."
    pytest tests/integration/ -v

# Run unit tests only
test-unit:
    @echo " Unit tests..."
    pytest tests/unit/ -v

# === EXAMPLES ===

# Run all examples
run-examples:
    @echo " Running examples..."
    @python examples/01_basic_validation.py
    @echo ""
    @python examples/02_custom_config.py
    @echo ""
    @python examples/03_batch_processing.py
    @echo ""
    @python examples/04_custom_check.py

# Run specific example
example NUM:
    @echo " Running example {{NUM}}..."
    @python examples/0{{NUM}}_*.py

# === PACKAGE MANAGEMENT ===

# Install package in development mode
install-dev:
    @echo " Installing in development mode..."
    pip install -e ".[dev]"
    @echo " Package installed"

# Install package with all extras
install-all:
    @echo " Installing with all extras..."
    pip install -e ".[all]"
    @echo " Package installed"

# Build package (wheel + sdist)
build:
    @echo " Building package..."
    rm -rf build/ dist/ *.egg-info
    python -m build
    @echo " Package built"
    @ls -lh dist/

# Check package before publish
check-package:
    @echo " Checking package..."
    twine check dist/*
    @echo " Package check OK"

# Publish to TestPyPI
publish-test:
    @echo " Publishing to TestPyPI..."
    twine upload --repository testpypi dist/*
    @echo " Published to TestPyPI"

# Publish to PyPI (production)
publish:
    @echo "  Publishing to PyPI (production)..."
    @echo "Press Enter to continue, Ctrl+C to abort"
    @read
    twine upload dist/*
    @echo " Published to PyPI"

# === CLEANUP ===

# Clean Python artifacts
clean:
    @echo " Cleaning Python artifacts..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache htmlcov .coverage build/ dist/
    @echo " Cleaning complete"

# Full cleanup + backup
cleanup:
    @echo " Full cleanup + backup..."
    bash scripts/cleanup.sh
    @echo " Cleanup complete"

# Restore from backup
restore:
    @echo "  Restoring from backup..."
    bash scripts/cleanup.sh restore

# === GIT ===

# Git sync (commit + push)
sync MESSAGE:
    @echo " Git sync..."
    python scripts/git_sync.py "{{MESSAGE}}"
    @echo " Sync complete"

# Create git tag
tag VERSION:
    @echo "  Creating tag {{VERSION}}..."
    git tag -a {{VERSION}} -m "Release {{VERSION}}"
    git push origin {{VERSION}}
    @echo " Tag {{VERSION}} created"

# === DEVELOPMENT ===

# Run all checks (format + lint + test)
check: format lint test
    @echo " All checks passed"

# Quick validation (lint + test)
validate: lint test
    @echo " Validation OK"

# === DOCUMENTATION ===

# Generate API docs (placeholder)
docs:
    @echo " Generating docs..."
    @echo "  Not implemented yet"

# Serve docs locally (placeholder)
docs-serve:
    @echo " Serving docs..."
    @echo "  Not implemented yet"

# === UTILITIES ===

# Show project stats
stats:
    @echo " Project Statistics"
    @echo "===================="
    @echo ""
    @echo "Production code:"
    @find dqf -name "*.py" ! -path "*/test*" ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1
    @echo ""
    @echo "Test code:"
    @find tests -name "*.py" ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1
    @echo ""
    @echo "Example code:"
    @find examples -name "*.py" ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1
    @echo ""
    @echo "Git commits:"
    @git log --oneline | wc -l
    @echo ""
    @echo "Coverage:"
    @pytest tests/ --cov=dqf --cov-report=term 2>/dev/null | grep TOTAL || echo "Run 'just test-cov' first"

# Check for non-ASCII characters
check-encoding:
    @python scripts/dqf_tools.py check-encoding

# Fix non-ASCII characters
fix-encoding:
    @python scripts/dqf_tools.py fix-encoding

# Run health checks
doctor:
    @python scripts/dqf_tools.py doctor

# List available commands
help:
    @just --list

# === ANTI-REGRESSION ===

# Full anti-regression check before commit
pre-commit:
    @just sanitize
    @echo ""
    @echo " PRE-COMMIT CHECKS PASSED"
    @echo "Ready to commit!"

# Full validation pipeline (CI/CD style)
ci: clean lint test-cov check-encoding
    @echo ""
    @echo " CI CHECKS PASSED"

# === RELEASE WORKFLOW ===

# Prepare release (bump version, build, check)
prepare-release VERSION:
    @echo " Preparing release {{VERSION}}..."
    @echo "1. Update version in pyproject.toml"
    @echo "2. Update CHANGELOG.md"
    @echo "3. Commit changes"
    @echo "4. Create tag"
    @just clean
    @just sanitize
    @just build
    @just check-package
    @echo " Release {{VERSION}} ready"
    @echo ""
    @echo "Next steps:"
    @echo "  1. Review dist/ files"
    @echo "  2. Test install: pip install dist/*.whl"
    @echo "  3. Publish test: just publish-test"
    @echo "  4. Publish prod: just publish"

# === SHORTCUTS ===

# Quick test + format
qtest: format test
    @echo " Quick test OK"

# Quick build + check
qbuild: build check-package
    @echo " Quick build OK"

# Optional: NixOS-specific (ignore if not using Nix)
nix-dev:
    @echo " Nix devShell..."
    nix develop