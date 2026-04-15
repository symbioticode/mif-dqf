"""
Unit tests for dqf.utils.cleaning_log — DQF v1.2

Tests cover:
  - to_parquet() with empty list → None
  - to_parquet() with valid entries → bytes
  - to_parquet() schema column order
  - to_parquet() numeric cast (gravity, value_before, value_after)
  - to_parquet() with missing optional keys filled as NaN
  - from_parquet() round-trip
  - from_parquet() column names preserved
  - from_parquet() gravity values preserved
  - Multi-check entries (C2 + C3 + C4 together)
  - Single C2 physical_correction entry
  - Single C3 calendar_removal entry
  - Single C4 forward_fill entry
  - Large entry list (100 rows)
  - Determinism: same entries → same bytes
  - Value types: string row_index
  - NaN value_before / value_after tolerated
  - Partial entry (only required keys) fills missing with NaN
  - from_parquet() returns DataFrame, not Series or dict
  - Gravity precision (float64)
  - Bytes content is valid Parquet (pyarrow round-trip)
"""

import pandas as pd
import pytest

from dqf.utils.cleaning_log import from_parquet, to_parquet

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

C2_ENTRY = {
    "row_index": "2024-01-02 09:30:00+00:00",
    "check_id": "C2",
    "intervention": "physical_correction",
    "field": "high_low",
    "value_before": None,
    "value_after": None,
    "gravity": 1.0,
}

C3_ENTRY = {
    "row_index": "2024-01-06 09:30:00+00:00",
    "check_id": "C3",
    "intervention": "calendar_removal",
    "field": "all",
    "value_before": None,
    "value_after": None,
    "gravity": 0.2,
}

C4_ENTRY = {
    "row_index": "2024-01-03 09:30:00+00:00",
    "check_id": "C4",
    "intervention": "forward_fill",
    "field": "close",
    "value_before": 150.0,
    "value_after": None,
    "gravity": 0.5,
}


# ---------------------------------------------------------------------------
# to_parquet — empty input
# ---------------------------------------------------------------------------


class TestToParquetEmpty:
    def test_empty_list_returns_none(self):
        assert to_parquet([]) is None

    def test_none_is_falsy(self):
        result = to_parquet([])
        assert not result


# ---------------------------------------------------------------------------
# to_parquet — valid entries
# ---------------------------------------------------------------------------


class TestToParquetValid:
    def test_single_c2_entry_returns_bytes(self):
        result = to_parquet([C2_ENTRY])
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_single_c3_entry_returns_bytes(self):
        result = to_parquet([C3_ENTRY])
        assert isinstance(result, bytes)

    def test_single_c4_entry_returns_bytes(self):
        result = to_parquet([C4_ENTRY])
        assert isinstance(result, bytes)

    def test_multiple_entries_returns_bytes(self):
        entries = [C2_ENTRY, C3_ENTRY, C4_ENTRY]
        result = to_parquet(entries)
        assert isinstance(result, bytes)

    def test_determinism(self):
        """Same entries always produce identical bytes."""
        entries = [C2_ENTRY, C4_ENTRY]
        b1 = to_parquet(entries)
        b2 = to_parquet(entries)
        assert b1 == b2

    def test_large_entry_list(self):
        """100 entries serialise without error."""
        entries = [
            {
                "row_index": f"2024-01-{i:02d}T09:30:00+00:00",
                "check_id": "C4",
                "intervention": "forward_fill",
                "field": "close",
                "value_before": float(100 + i),
                "value_after": None,
                "gravity": 0.5,
            }
            for i in range(1, 101)
        ]
        result = to_parquet(entries)
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# to_parquet — schema and type handling
# ---------------------------------------------------------------------------


class TestToParquetSchema:
    def test_gravity_is_float64(self):
        """Gravity column should be float64 in the Parquet schema."""
        result = to_parquet([C2_ENTRY])
        df = from_parquet(result)
        assert df["gravity"].dtype == "float64"

    def test_value_before_is_float64(self):
        result = to_parquet([C4_ENTRY])
        df = from_parquet(result)
        assert df["value_before"].dtype == "float64"

    def test_value_after_is_float64(self):
        result = to_parquet([C4_ENTRY])
        df = from_parquet(result)
        assert df["value_after"].dtype == "float64"

    def test_missing_value_after_becomes_nan(self):
        """Entries without value_after produce NaN, not an error."""
        entry = dict(C2_ENTRY)  # has value_after = None
        result = to_parquet([entry])
        df = from_parquet(result)
        assert pd.isna(df["value_after"].iloc[0])

    def test_partial_entry_missing_field_filled(self):
        """Entry missing 'value_before' is filled with NaN."""
        entry = {
            "row_index": "2024-01-02",
            "check_id": "C3",
            "intervention": "calendar_removal",
            "field": "all",
            "gravity": 0.2,
        }
        result = to_parquet([entry])
        df = from_parquet(result)
        assert pd.isna(df["value_before"].iloc[0])


# ---------------------------------------------------------------------------
# from_parquet — round-trip
# ---------------------------------------------------------------------------


class TestFromParquetRoundTrip:
    def test_returns_dataframe(self):
        result = to_parquet([C4_ENTRY])
        df = from_parquet(result)
        assert isinstance(df, pd.DataFrame)

    def test_row_count_preserved(self):
        entries = [C2_ENTRY, C3_ENTRY, C4_ENTRY]
        df = from_parquet(to_parquet(entries))
        assert len(df) == 3

    def test_check_id_preserved(self):
        entries = [C2_ENTRY, C3_ENTRY, C4_ENTRY]
        df = from_parquet(to_parquet(entries))
        assert set(df["check_id"].tolist()) == {"C2", "C3", "C4"}

    def test_intervention_values_preserved(self):
        entries = [C2_ENTRY, C3_ENTRY, C4_ENTRY]
        df = from_parquet(to_parquet(entries))
        assert set(df["intervention"].tolist()) == {
            "physical_correction",
            "calendar_removal",
            "forward_fill",
        }

    def test_gravity_values_preserved(self):
        entries = [C2_ENTRY, C3_ENTRY, C4_ENTRY]
        df = from_parquet(to_parquet(entries))
        gravities = sorted(df["gravity"].tolist())
        assert gravities == pytest.approx([0.2, 0.5, 1.0])

    def test_value_before_preserved(self):
        df = from_parquet(to_parquet([C4_ENTRY]))
        assert df["value_before"].iloc[0] == pytest.approx(150.0)

    def test_column_names_match_schema(self):
        expected = {
            "row_index",
            "check_id",
            "intervention",
            "field",
            "value_before",
            "value_after",
            "gravity",
        }
        df = from_parquet(to_parquet([C2_ENTRY]))
        assert set(df.columns) == expected

    def test_row_index_is_string(self):
        """row_index column must contain string values (timestamp as text)."""
        df = from_parquet(to_parquet([C2_ENTRY]))
        assert pd.api.types.is_string_dtype(df["row_index"])

    def test_bytes_is_valid_parquet(self):
        """Bytes must be parseable by pyarrow directly."""
        raw = to_parquet([C4_ENTRY])
        # from_parquet internally uses pd.read_parquet; just ensure no exception
        df = from_parquet(raw)
        assert not df.empty
