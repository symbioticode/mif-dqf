"""
Unit tests for DQF v1.1 — utils/mpi.py

Covers:
  - InterventionLog: construction, add(), total_weighted(), total_count(), __add__
  - compute_mpi: zero interventions, partial, full, clamping, edge cases
  - Error paths: invalid intervention type, negative count, n_total_points <= 0
"""

import pytest

from dqf.utils.mpi import GRAVITY, InterventionLog, compute_mpi


# ---------------------------------------------------------------------------
# InterventionLog — construction
# ---------------------------------------------------------------------------


class TestInterventionLogConstruction:
    def test_default_zero(self):
        log = InterventionLog()
        assert log.physical_corrections == 0
        assert log.forward_fills == 0
        assert log.calendar_removals == 0

    def test_explicit_values(self):
        log = InterventionLog(physical_corrections=3, forward_fills=5, calendar_removals=2)
        assert log.physical_corrections == 3
        assert log.forward_fills == 5
        assert log.calendar_removals == 2

    def test_total_weighted_zero_by_default(self):
        assert InterventionLog().total_weighted() == 0.0

    def test_total_count_zero_by_default(self):
        assert InterventionLog().total_count() == 0


# ---------------------------------------------------------------------------
# InterventionLog.add()
# ---------------------------------------------------------------------------


class TestInterventionLogAdd:
    def test_add_physical_correction(self):
        log = InterventionLog()
        log.add("physical_correction", 3)
        assert log.physical_corrections == 3

    def test_add_forward_fill(self):
        log = InterventionLog()
        log.add("forward_fill", 7)
        assert log.forward_fills == 7

    def test_add_calendar_removal(self):
        log = InterventionLog()
        log.add("calendar_removal", 2)
        assert log.calendar_removals == 2

    def test_add_default_count_is_one(self):
        log = InterventionLog()
        log.add("physical_correction")
        assert log.physical_corrections == 1

    def test_add_accumulates(self):
        log = InterventionLog()
        log.add("forward_fill", 3)
        log.add("forward_fill", 4)
        assert log.forward_fills == 7

    def test_add_zero_count_is_noop(self):
        log = InterventionLog()
        log.add("physical_correction", 0)
        assert log.physical_corrections == 0

    def test_add_unknown_type_raises(self):
        log = InterventionLog()
        with pytest.raises(ValueError, match="Unknown intervention type"):
            log.add("magic_fix", 1)

    def test_add_negative_count_raises(self):
        log = InterventionLog()
        with pytest.raises(ValueError, match="count must be >= 0"):
            log.add("forward_fill", -1)


# ---------------------------------------------------------------------------
# InterventionLog.total_weighted()
# ---------------------------------------------------------------------------


class TestInterventionLogWeighted:
    def test_single_physical(self):
        log = InterventionLog(physical_corrections=2)
        assert log.total_weighted() == 2 * GRAVITY["physical_correction"]

    def test_single_ffill(self):
        log = InterventionLog(forward_fills=4)
        assert log.total_weighted() == 4 * GRAVITY["forward_fill"]

    def test_single_calendar(self):
        log = InterventionLog(calendar_removals=10)
        assert log.total_weighted() == 10 * GRAVITY["calendar_removal"]

    def test_mixed(self):
        log = InterventionLog(physical_corrections=1, forward_fills=2, calendar_removals=5)
        expected = (
            1 * GRAVITY["physical_correction"]
            + 2 * GRAVITY["forward_fill"]
            + 5 * GRAVITY["calendar_removal"]
        )
        assert log.total_weighted() == pytest.approx(expected)

    def test_total_count(self):
        log = InterventionLog(physical_corrections=1, forward_fills=2, calendar_removals=3)
        assert log.total_count() == 6


# ---------------------------------------------------------------------------
# InterventionLog.__add__()
# ---------------------------------------------------------------------------


class TestInterventionLogMerge:
    def test_add_two_logs(self):
        a = InterventionLog(physical_corrections=1, forward_fills=2, calendar_removals=3)
        b = InterventionLog(physical_corrections=4, forward_fills=0, calendar_removals=1)
        merged = a + b
        assert merged.physical_corrections == 5
        assert merged.forward_fills == 2
        assert merged.calendar_removals == 4

    def test_add_with_empty(self):
        a = InterventionLog(physical_corrections=3)
        b = InterventionLog()
        assert (a + b).physical_corrections == 3

    def test_originals_unchanged_after_merge(self):
        a = InterventionLog(physical_corrections=2)
        b = InterventionLog(physical_corrections=5)
        _ = a + b
        assert a.physical_corrections == 2
        assert b.physical_corrections == 5


# ---------------------------------------------------------------------------
# compute_mpi()
# ---------------------------------------------------------------------------


class TestComputeMpi:
    def test_zero_interventions_returns_100(self):
        log = InterventionLog()
        assert compute_mpi(log, 1000) == 100.0

    def test_physical_correction_cost(self):
        # 2 physical corrections on 1000 points → 2*1.0/1000 = 0.002 → 99.8
        log = InterventionLog(physical_corrections=2)
        assert compute_mpi(log, 1000) == pytest.approx(99.8)

    def test_forward_fill_cost(self):
        # 10 ffill on 1000 points → 10*0.5/1000 = 0.005 → 99.5
        log = InterventionLog(forward_fills=10)
        assert compute_mpi(log, 1000) == pytest.approx(99.5)

    def test_calendar_removal_cost(self):
        # 20 removals on 1000 points → 20*0.2/1000 = 0.004 → 99.6
        log = InterventionLog(calendar_removals=20)
        assert compute_mpi(log, 1000) == pytest.approx(99.6)

    def test_clamped_to_zero_when_overwhelmed(self):
        # Extreme: more weighted interventions than total points
        log = InterventionLog(physical_corrections=2000)
        assert compute_mpi(log, 100) == 0.0

    def test_clamped_max_100(self):
        # Should never exceed 100
        log = InterventionLog()
        assert compute_mpi(log, 1) == 100.0

    def test_n_total_points_zero_raises(self):
        log = InterventionLog()
        with pytest.raises(ValueError, match="n_total_points must be > 0"):
            compute_mpi(log, 0)

    def test_n_total_points_negative_raises(self):
        log = InterventionLog()
        with pytest.raises(ValueError, match="n_total_points must be > 0"):
            compute_mpi(log, -5)

    def test_n_total_points_formula(self):
        # n = rows * 5 ; 100 rows → 500 points
        # 5 physical corrections: 5*1.0/500 = 1% → MPI = 99.0
        log = InterventionLog(physical_corrections=5)
        assert compute_mpi(log, 500) == pytest.approx(99.0)

    def test_mpi_spec_interpretation_80_to_99(self):
        # Minor interpolation range — stays above 80
        log = InterventionLog(forward_fills=10)
        mpi = compute_mpi(log, 1000)
        assert 80.0 <= mpi <= 100.0
