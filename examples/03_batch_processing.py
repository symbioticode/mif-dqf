#!/usr/bin/env python3
"""
DQF Example 03: Batch Processing — v1.1

Demonstrates:
- Validating multiple symbols in DIAGNOSTIC mode
- Aggregating MPI/gate across a portfolio
- Filtering CERTIFIED vs VOID datasets
- Generating a consolidated CSV report
- Custom ffill thresholds for a strict pipeline

Usage:
    python examples/03_batch_processing.py
"""

import sys
from pathlib import Path

import pandas as pd

from dqf import DQFConfig, DQFMode, DQFValidator

# ---------------------------------------------------------------------------
# Synthetic data factory
# ---------------------------------------------------------------------------


def create_sample_datasets() -> dict[str, pd.DataFrame]:
    """Create sample datasets for several symbols."""
    symbols = ["BTC-USD", "ETH-USD", "SPY", "GLD", "EUR-USD"]
    datasets: dict[str, pd.DataFrame] = {}

    # BTC/ETH/EUR-USD: daily (includes weekends — CRYPTO_247 / FOREX_245)
    # SPY / GLD: weekday-only (NYSE)
    for symbol in symbols:
        base_prices = {
            "BTC-USD": 45_000.0,
            "ETH-USD": 2_500.0,
            "SPY": 450.0,
            "GLD": 180.0,
            "EUR-USD": 1.08,
        }
        base = base_prices[symbol]

        if symbol in ("SPY", "GLD"):
            dates = pd.bdate_range("2024-01-02", periods=60, freq="B", tz="UTC")
        else:
            dates = pd.date_range("2024-01-01", periods=60, freq="D", tz="UTC")

        n = len(dates)
        data = pd.DataFrame(
            {
                "open": [base + i * 0.1 for i in range(n)],
                "high": [base * 1.01 + i * 0.1 for i in range(n)],
                "low": [base * 0.99 + i * 0.1 for i in range(n)],
                "close": [base + i * 0.1 for i in range(n)],
                "volume": [1_000_000 + i * 1_000 for i in range(n)],
            },
            index=dates,
        )

        # Introduce a forward-fill run in EUR-USD
        if symbol == "EUR-USD":
            data.loc[data.index[10:15], "close"] = data.loc[data.index[9], "close"]

        # Introduce OHLCV violation in GLD
        if symbol == "GLD":
            data.loc[data.index[50], "high"] = data.loc[data.index[50], "low"] - 1

        datasets[symbol] = data

    return datasets


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------

CALENDAR_MAP = {
    "BTC-USD": "CRYPTO_247",
    "ETH-USD": "CRYPTO_247",
    "SPY": "NYSE",
    "GLD": "NYSE",
    "EUR-USD": "FOREX_245",
}


def batch_validate(
    datasets: dict[str, pd.DataFrame],
    config: DQFConfig,
    mode_label: str = "DIAGNOSTIC",
) -> dict[str, object]:
    """Validate a dict of DataFrames; returns {symbol: DQFReport | None}."""
    print(f"Batch validation — mode={mode_label}")
    print("-" * 70)

    validator = DQFValidator(config)
    results: dict[str, object] = {}

    for symbol, data in datasets.items():
        calendar = CALENDAR_MAP.get(symbol)
        try:
            if config.mode == DQFMode.CERTIFICATION:
                report = validator.validate(data, calendar=calendar)
            else:
                report = validator.validate(data)
            results[symbol] = report

            status = report.overall_status
            mpi = report.purity_index
            print(f"  {symbol:12s}  {status:11s}  MPI={mpi:.1f}  gate={report.precondition_gate}")

        except Exception as exc:
            print(f"  {symbol:12s}  ERROR — {exc}")
            results[symbol] = None

    print()
    return results


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def print_summary(results: dict[str, object]) -> None:
    """Print aggregate summary."""
    print("=" * 70)
    print("BATCH VALIDATION SUMMARY")
    print("=" * 70)

    certified = [s for s, r in results.items() if r and r.is_certified]
    warned = [s for s, r in results.items() if r and r.overall_status == "WARNING"]
    voided = [s for s, r in results.items() if r and r.overall_status == "VOID"]
    errors = [s for s, r in results.items() if r is None]

    print(f"  Total     : {len(results)}")
    print(f"  CERTIFIED : {len(certified)}  {certified}")
    print(f"  WARNING   : {len(warned)}   {warned}")
    print(f"  VOID      : {len(voided)}   {voided}")
    print(f"  ERROR     : {len(errors)}   {errors}")
    print()

    if certified:
        avg_mpi = sum(r.purity_index for s, r in results.items() if r and r.is_certified) / len(
            certified
        )
        print(f"  Avg MPI (certified) : {avg_mpi:.1f}/100")
    print()


def filter_certified(
    datasets: dict[str, pd.DataFrame],
    results: dict[str, object],
) -> dict[str, pd.DataFrame]:
    """Return only certified DataFrames."""
    clean = {s: r.cleaned_data for s, r in results.items() if r and r.is_certified}
    print(f"Certified datasets : {len(clean)}/{len(datasets)}")
    for symbol in clean:
        print(f"  OK  {symbol}")
    print()
    return clean


def export_results(results: dict[str, object], output_dir: Path) -> None:
    """Write per-symbol JSON manifests."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for symbol, report in results.items():
        if report is None:
            continue
        safe = symbol.replace("/", "_")
        sym_dir = output_dir / safe
        sym_dir.mkdir(exist_ok=True)
        (sym_dir / "manifest.json").write_text(report.to_json())
        if report.is_certified:
            report.cleaned_data.to_csv(sym_dir / f"{safe}_clean.csv")
    print(f"Results saved to : {output_dir}")
    print()


def create_consolidated_csv(results: dict[str, object], output_path: Path) -> None:
    """Write a one-row-per-symbol CSV summary."""
    rows = []
    for symbol, report in results.items():
        if report is None:
            rows.append(
                {"symbol": symbol, "status": "ERROR", "mpi": 0.0, "gate": 0.0, "mif_uid": ""}
            )
        else:
            rows.append(
                {
                    "symbol": symbol,
                    "status": report.overall_status,
                    "mpi": report.purity_index,
                    "gate": report.precondition_gate,
                    "mif_uid": report.mif_uid,
                }
            )
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Consolidated CSV : {output_path}")
    print()


# ---------------------------------------------------------------------------
# Main examples
# ---------------------------------------------------------------------------


def example_basic_batch():
    """Basic batch in DIAGNOSTIC mode."""
    print("=" * 70)
    print("Example 1: Basic Batch (DIAGNOSTIC mode)")
    print("=" * 70)
    print()

    datasets = create_sample_datasets()
    config = DQFConfig(mode=DQFMode.DIAGNOSTIC)

    results = batch_validate(datasets, config, mode_label="DIAGNOSTIC")
    print_summary(results)
    filter_certified(datasets, results)

    output_dir = Path("_work/examples/batch_results")
    export_results(results, output_dir)
    create_consolidated_csv(results, output_dir / "consolidated_report.csv")


def example_strict_batch():
    """Strict batch in CERTIFICATION mode with tight ffill threshold."""
    print("=" * 70)
    print("Example 2: Strict Batch (CERTIFICATION mode)")
    print("=" * 70)
    print()

    datasets = create_sample_datasets()
    config = DQFConfig(
        mode=DQFMode.CERTIFICATION,
        c4_warn_threshold=1,  # warn after 1 consecutive repeat
        c4_max_consecutive_ffill=2,  # fail after 2
    )

    results = batch_validate(datasets, config, mode_label="CERTIFICATION")
    print_summary(results)

    print("Note: GLD fails C2 (High < Low). EUR-USD may trigger C4 warning.")
    print()


def main():
    print("\n")
    print("DQF v1.1 — Batch Processing Examples")
    print("=" * 70)
    print()

    example_basic_batch()

    if sys.stdin.isatty():
        input("Press Enter to run strict certification batch...")
    print()

    example_strict_batch()

    print("=" * 70)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 70)
    print()
    print("Key takeaways:")
    print("  - DIAGNOSTIC mode: runs all checks, no calendar required")
    print("  - CERTIFICATION mode: calendar required, VOID if CORE check fails")
    print(
        "  - report.purity_index (0-100) and report.precondition_gate replace checks_passed/total"
    )
    print("  - report.is_certified is the primary pass/fail signal")
    print()


if __name__ == "__main__":
    main()
