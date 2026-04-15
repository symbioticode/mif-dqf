"""
CleaningLog — DQF v1.2

Serialises per-row intervention records collected by C2, C3, C4 into
Parquet bytes suitable for embedding in the MIF-Lite manifest or storing
as an external artefact (Phase 2).

Schema columns
--------------
row_index   : str  — string representation of the affected row's index (timestamp)
check_id    : str  — which check emitted this entry ("C2", "C3", "C4")
intervention: str  — "physical_correction" | "forward_fill" | "calendar_removal"
field       : str  — affected OHLCV field ("open", "high", "low", "close",
                      "volume", "high_low", "all", …) or check-specific label
value_before: float — value at the row before correction (NaN if not applicable)
value_after : float — value after correction (NaN in Phase 1 — detect only)
gravity     : float — MPI weight: 1.0 physical, 0.5 ffill, 0.2 calendar removal
"""

from __future__ import annotations

import io

import pandas as pd

# Canonical column order for the Parquet schema
_COLUMNS: list[str] = [
    "row_index",
    "check_id",
    "intervention",
    "field",
    "value_before",
    "value_after",
    "gravity",
]


def to_parquet(entries: list[dict]) -> bytes | None:
    """
    Serialise a list of cleaning entry dicts to in-memory Parquet bytes.

    Args:
        entries: List of dicts, each with keys matching ``_COLUMNS``.
                 Missing keys are filled with NaN / None.

    Returns:
        Parquet bytes if ``entries`` is non-empty, ``None`` otherwise.
    """
    if not entries:
        return None

    df = pd.DataFrame(entries)

    # Ensure all schema columns are present
    for col in _COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[_COLUMNS]

    # Numeric columns: cast to float64 so Parquet schema is deterministic
    for col in ("value_before", "value_after", "gravity"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def from_parquet(data: bytes) -> pd.DataFrame:
    """
    Deserialise Parquet bytes back to a cleaning log DataFrame.

    Args:
        data: Raw Parquet bytes produced by ``to_parquet()``.

    Returns:
        DataFrame with columns matching ``_COLUMNS``.
    """
    return pd.read_parquet(io.BytesIO(data))
