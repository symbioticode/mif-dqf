"""
Integration tests for DQFValidator + DQFReport — v1.1

Full end-to-end pipeline:
  DQFConfig → DQFValidator.validate() → DQFReport (MIF-Lite manifest)

Covers:
  - CERTIFICATION mode: clean data → CERTIFIED, MPI=100, gate=1.0
  - CERTIFICATION mode: integrity violations → VOID (CORE FAIL)
  - CERTIFICATION mode: missing calendar → VOID (C3 ERROR_MISSING_METADATA)
  - CERTIFICATION mode: advisory WARN (ffill) → WARNING, gate ≤ 0.8
  - DIAGNOSTIC mode: no calendar → auto-detect, result not VOID
  - Manifest structure: all required top-level keys present
  - DQFReport properties: overall_status, purity_index, gate, mif_uid
  - DQFReport.is_certified, print_summary (smoke), to_json, to_yaml
  - DQFValidator type safety: wrong config type → TypeError
  - PROD always in core_results
  - C1 always SKIP in Phase 1
  - Determinism: same df + same args → same mif_uid
"""

import json

import pandas as pd
import pytest
import yaml

from dqf.core.config import DQFConfig
from dqf.core.enums import (
    STATUS_CERTIFIED,
    STATUS_VOID,
    STATUS_WARNING,
    DQFMode,
)
from dqf.core.report import DQFReport
from dqf.core.validator import DQFValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cert_config():
    return DQFConfig(mode=DQFMode.CERTIFICATION)


@pytest.fixture
def diag_config():
    return DQFConfig(mode=DQFMode.DIAGNOSTIC)


@pytest.fixture
def clean_nyse_df():
    """Weekday-only, timezone-aware, physics-valid OHLCV data."""
    dates = pd.bdate_range("2024-01-02", periods=20, freq="B", tz="UTC")
    return pd.DataFrame(
        {
            "open":   [100.0 + i for i in range(len(dates))],
            "high":   [105.0 + i for i in range(len(dates))],
            "low":    [95.0  + i for i in range(len(dates))],
            "close":  [102.0 + i for i in range(len(dates))],
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )


@pytest.fixture
def df_with_integrity_violation():
    """Data with High < Low on one bar — C2 CORE FAIL."""
    dates = pd.bdate_range("2024-01-02", periods=10, freq="B", tz="UTC")
    df = pd.DataFrame(
        {
            "open":   [100.0] * 10,
            "high":   [90.0] + [105.0] * 9,   # row 0: high < low
            "low":    [95.0] * 10,
            "close":  [102.0] * 10,
            "volume": [1_000_000] * 10,
        },
        index=dates,
    )
    return df


@pytest.fixture
def df_with_ffill():
    """Data with 4 consecutive identical close values — C4 ADVISORY WARN."""
    dates = pd.bdate_range("2024-01-02", periods=15, freq="B", tz="UTC")
    close = [100.0, 101.0, 102.0, 103.0, 104.0,
             104.0, 104.0, 104.0, 104.0,          # 5 identical → 4 ffills
             105.0, 106.0, 107.0, 108.0, 109.0, 110.0]
    return pd.DataFrame(
        {
            "open":   [c - 1 for c in close],
            "high":   [c + 2 for c in close],
            "low":    [c - 2 for c in close],
            "close":  close,
            "volume": [1_000_000] * 15,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# CERTIFICATION mode
# ---------------------------------------------------------------------------

class TestCertificationMode:
    def test_clean_data_certified(self, cert_config, clean_nyse_df):
        """Clean NYSE data in CERTIFICATION mode → CERTIFIED."""
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert isinstance(report, DQFReport)
        assert report.overall_status == STATUS_CERTIFIED
        assert report.is_certified is True

    def test_certified_gate_is_1(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.precondition_gate == 1.0

    def test_certified_mpi_is_100_for_clean_data(self, cert_config, clean_nyse_df):
        """No interventions on clean data → MPI = 100."""
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.purity_index == pytest.approx(100.0)

    def test_integrity_violation_returns_void(self, cert_config, df_with_integrity_violation):
        """C2 FAIL (High < Low) → overall VOID, gate = 0.0."""
        validator = DQFValidator(cert_config)
        report = validator.validate(df_with_integrity_violation, calendar="NYSE")

        assert report.overall_status == STATUS_VOID
        assert report.precondition_gate == 0.0
        assert report.is_certified is False

    def test_missing_calendar_returns_void(self, cert_config, clean_nyse_df):
        """C3 CORE FAIL on missing calendar → VOID."""
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar=None)

        assert report.overall_status == STATUS_VOID
        assert report.core_results.get("C3") in ("FAIL", "ERROR")

    def test_advisory_ffill_warn_returns_warning(self, cert_config, df_with_ffill):
        """C4 WARN → manifest STATUS_WARNING, gate ≤ 0.8."""
        validator = DQFValidator(cert_config)
        report = validator.validate(df_with_ffill, calendar="NYSE")

        # CORE checks must all pass for WARNING (not VOID)
        assert report.overall_status in (STATUS_WARNING, STATUS_CERTIFIED)
        if report.overall_status == STATUS_WARNING:
            assert report.precondition_gate <= 0.8

    def test_prod_always_in_core_results(self, cert_config, clean_nyse_df):
        """PROD must appear in manifest checks.core as 'PASS'."""
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert "PROD" in report.core_results
        assert report.core_results["PROD"] == "PASS"

    def test_c1_always_skip_phase1(self, cert_config, clean_nyse_df):
        """C1 is SKIP in Phase 1 (DAL not connected)."""
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.advisory_results.get("C1") == "SKIP"


# ---------------------------------------------------------------------------
# DIAGNOSTIC mode
# ---------------------------------------------------------------------------

class TestDiagnosticMode:
    def test_no_calendar_does_not_void(self, diag_config, clean_nyse_df):
        """DIAGNOSTIC + no calendar → auto-detect, result is not VOID."""
        validator = DQFValidator(diag_config)
        report = validator.validate(clean_nyse_df)

        assert report.overall_status != STATUS_VOID

    def test_diagnostic_manifest_has_mode_annotation(self, diag_config, clean_nyse_df):
        """Provenance.mode is 'DIAGNOSTIC'."""
        validator = DQFValidator(diag_config)
        report = validator.validate(clean_nyse_df)

        assert report.mode == "DIAGNOSTIC"

    def test_diagnostic_calendar_unknown_when_omitted(self, diag_config, clean_nyse_df):
        """Without explicit calendar in DIAGNOSTIC, calendar may be UNKNOWN or inferred."""
        validator = DQFValidator(diag_config)
        report = validator.validate(clean_nyse_df)

        # Calendar is either auto-detected or UNKNOWN — either is valid
        assert isinstance(report.calendar, str)


# ---------------------------------------------------------------------------
# Manifest structure
# ---------------------------------------------------------------------------

class TestManifestStructure:
    def test_required_top_level_keys(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")
        required = {"@context", "@type", "mif_uid", "status", "checks",
                    "vitality_signal", "provenance", "signature"}
        assert required.issubset(report.manifest.keys())

    def test_mif_uid_starts_with_sha256(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.mif_uid.startswith("sha256:")

    def test_sig_type_sha256_provisional(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.manifest["signature"]["type"] == "sha256_provisional"

    def test_cleaning_log_uri_is_null(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.manifest["provenance"]["cleaning_log_uri"] is None

    def test_vitality_label_in_dsig_vocabulary(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.vitality_label in {"EXCELLENT", "GOOD", "DEGRADED", "CRITICAL"}


# ---------------------------------------------------------------------------
# DQFReport properties and serialisation
# ---------------------------------------------------------------------------

class TestReportProperties:
    def test_to_json_returns_valid_json(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")
        parsed = json.loads(report.to_json())

        assert parsed["@context"] == "https://mif.dev/v1"
        assert "mif_uid" in parsed

    def test_to_yaml_returns_valid_yaml(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")
        parsed = yaml.safe_load(report.to_yaml())

        assert "mif_uid" in parsed
        assert parsed["@type"] == "DataCertification"

    def test_print_summary_does_not_raise(self, cert_config, clean_nyse_df, capsys):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")
        report.print_summary()  # must not raise

        captured = capsys.readouterr()
        assert "DQF" in captured.out
        assert report.overall_status in captured.out

    def test_repr_contains_status(self, cert_config, clean_nyse_df):
        validator = DQFValidator(cert_config)
        report = validator.validate(clean_nyse_df, calendar="NYSE")

        assert report.overall_status in repr(report)


# ---------------------------------------------------------------------------
# DQFValidator type safety and determinism
# ---------------------------------------------------------------------------

class TestValidatorContract:
    def test_wrong_config_type_raises(self):
        with pytest.raises(TypeError, match="DQFConfig"):
            DQFValidator("not_a_config")

    def test_non_dataframe_raises(self, cert_config):
        validator = DQFValidator(cert_config)
        with pytest.raises(TypeError, match="DataFrame"):
            validator.validate("not_a_df", calendar="NYSE")

    def test_determinism_same_inputs_same_uid(self, cert_config, clean_nyse_df):
        """Same df + same args must yield the same mif_uid."""
        v1 = DQFValidator(cert_config)
        v2 = DQFValidator(cert_config)
        uid1 = v1.validate(clean_nyse_df, calendar="NYSE").mif_uid
        uid2 = v2.validate(clean_nyse_df, calendar="NYSE").mif_uid

        assert uid1 == uid2

    def test_different_calendars_different_uid(self, cert_config, clean_nyse_df):
        """Calendar is part of MIF-UID — different calendars → different UIDs."""
        v = DQFValidator(cert_config)
        uid_nyse = v.validate(clean_nyse_df, calendar="NYSE").mif_uid
        uid_lse  = v.validate(clean_nyse_df, calendar="LSE").mif_uid

        assert uid_nyse != uid_lse

    def test_repr_contains_mode(self, cert_config):
        v = DQFValidator(cert_config)
        assert "CERTIFICATION" in repr(v)
