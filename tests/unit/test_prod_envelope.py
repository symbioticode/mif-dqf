"""
Unit tests for DQF v1.1 — core/prod_envelope.py

Covers:
  - _compute_overall_status: CERTIFIED, WARNING, VOID (FAIL/ERROR in core)
  - build(): manifest structure, all required keys and types
  - precondition_gate: correct values per status, MPI cap for WARNING
  - mif_uid: format, determinism, sensitivity to inputs
  - signature: type always "sha256_provisional", value is hex string
  - provenance: cleaning_log_uri always null, mode/calendar/version present
  - vitality_signal: label in D-SIG vocabulary, score in [0,100]
  - to_json(): valid JSON, round-trip
  - Invariants from spec §3–§7
"""

import json

import pytest

from dqf.core.enums import (
    STATUS_CERTIFIED,
    STATUS_VOID,
    STATUS_WARNING,
    DQFMode,
)
from dqf.core.prod_envelope import PRODEnvelope, _mpi_to_vitality_score, _vitality_label
from dqf.utils.mpi import InterventionLog

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

CORE_PASS = {"PROD": "PASS", "C2": "PASS", "C3": "PASS", "C5": "PASS"}
ADVISORY_CLEAN = {"C1": "SKIP", "C4": "PASS"}
ADVISORY_WARN = {"C1": "SKIP", "C4": "WARN"}


def _make_envelope(
    mode=DQFMode.CERTIFICATION,
    core_results=None,
    advisory_results=None,
    raw_data_hash="sha256:abc123",
    dqf_version="1.1.0",
    calendar="NYSE",
    intervention_log=None,
    n_total_points=500,
):
    return PRODEnvelope(
        mode=mode,
        core_results=core_results if core_results is not None else dict(CORE_PASS),
        advisory_results=advisory_results if advisory_results is not None else dict(ADVISORY_CLEAN),
        raw_data_hash=raw_data_hash,
        dqf_version=dqf_version,
        calendar=calendar,
        intervention_log=intervention_log or InterventionLog(),
        n_total_points=n_total_points,
    )


# ---------------------------------------------------------------------------
# _compute_overall_status
# ---------------------------------------------------------------------------


class TestOverallStatus:
    def test_all_pass_returns_certified(self):
        env = _make_envelope()
        assert env._compute_overall_status() == STATUS_CERTIFIED

    def test_advisory_warn_returns_warning(self):
        env = _make_envelope(advisory_results=ADVISORY_WARN)
        assert env._compute_overall_status() == STATUS_WARNING

    def test_core_fail_returns_void(self):
        core = {**CORE_PASS, "C2": "FAIL"}
        env = _make_envelope(core_results=core)
        assert env._compute_overall_status() == STATUS_VOID

    def test_core_error_returns_void(self):
        core = {**CORE_PASS, "C3": "ERROR"}
        env = _make_envelope(core_results=core)
        assert env._compute_overall_status() == STATUS_VOID

    def test_core_fail_beats_advisory_warn(self):
        # Even if advisory has WARN, CORE FAIL → VOID (not WARNING)
        core = {**CORE_PASS, "C5": "FAIL"}
        env = _make_envelope(core_results=core, advisory_results=ADVISORY_WARN)
        assert env._compute_overall_status() == STATUS_VOID

    def test_advisory_skip_not_warn(self):
        # SKIP is not WARN — should remain CERTIFIED
        advisory = {"C1": "SKIP", "C4": "SKIP"}
        env = _make_envelope(advisory_results=advisory)
        assert env._compute_overall_status() == STATUS_CERTIFIED


# ---------------------------------------------------------------------------
# build() — manifest structure
# ---------------------------------------------------------------------------


class TestManifestStructure:
    def test_top_level_keys(self):
        manifest = _make_envelope().build()
        required = {
            "@context",
            "@type",
            "mif_uid",
            "status",
            "checks",
            "vitality_signal",
            "provenance",
            "signature",
        }
        assert required.issubset(manifest.keys())

    def test_context_and_type(self):
        manifest = _make_envelope().build()
        assert manifest["@context"] == "https://mif.dev/v1"
        assert manifest["@type"] == "DataCertification"

    def test_status_keys(self):
        s = _make_envelope().build()["status"]
        assert "overall" in s
        assert "precondition_gate" in s
        assert "purity_index" in s

    def test_checks_keys(self):
        c = _make_envelope().build()["checks"]
        assert "core" in c
        assert "advisory" in c

    def test_provenance_keys(self):
        p = _make_envelope().build()["provenance"]
        for k in ("dqf_version", "mode", "source_hash", "calendar", "cleaning_log_uri"):
            assert k in p

    def test_signature_keys(self):
        sig = _make_envelope().build()["signature"]
        assert "type" in sig
        assert "value" in sig

    def test_vitality_signal_keys(self):
        v = _make_envelope().build()["vitality_signal"]
        assert "score" in v
        assert "label" in v
        assert "trend" in v


# ---------------------------------------------------------------------------
# Invariants (spec §3–§7)
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_sig_type_always_sha256_provisional(self):
        for mode in (DQFMode.CERTIFICATION, DQFMode.DIAGNOSTIC):
            manifest = _make_envelope(mode=mode).build()
            assert manifest["signature"]["type"] == "sha256_provisional"

    def test_cleaning_log_uri_always_null(self):
        manifest = _make_envelope().build()
        assert manifest["provenance"]["cleaning_log_uri"] is None

    def test_vitality_label_in_dsig_vocabulary(self):
        valid_labels = {"EXCELLENT", "GOOD", "DEGRADED", "CRITICAL"}
        for mode in (DQFMode.CERTIFICATION, DQFMode.DIAGNOSTIC):
            manifest = _make_envelope(mode=mode).build()
            assert manifest["vitality_signal"]["label"] in valid_labels

    def test_purity_index_in_range(self):
        manifest = _make_envelope().build()
        mpi = manifest["status"]["purity_index"]
        assert 0.0 <= mpi <= 100.0

    def test_vitality_score_in_range(self):
        manifest = _make_envelope().build()
        score = manifest["vitality_signal"]["score"]
        assert 0 <= score <= 100

    def test_trend_is_stable_phase1(self):
        manifest = _make_envelope().build()
        assert manifest["vitality_signal"]["trend"] == "STABLE"


# ---------------------------------------------------------------------------
# precondition_gate (spec §7)
# ---------------------------------------------------------------------------


class TestPreconditionGate:
    def test_certified_gate_is_1(self):
        manifest = _make_envelope().build()
        assert manifest["status"]["precondition_gate"] == 1.0
        assert manifest["status"]["overall"] == STATUS_CERTIFIED

    def test_void_gate_is_0(self):
        core = {**CORE_PASS, "C2": "FAIL"}
        manifest = _make_envelope(core_results=core).build()
        assert manifest["status"]["precondition_gate"] == 0.0
        assert manifest["status"]["overall"] == STATUS_VOID

    def test_warning_gate_max_0_8_when_mpi_high(self):
        # High MPI (no interventions) → gate = min(0.8, 100/100) = 0.8
        manifest = _make_envelope(advisory_results=ADVISORY_WARN).build()
        assert manifest["status"]["overall"] == STATUS_WARNING
        assert manifest["status"]["precondition_gate"] <= 0.8

    def test_warning_gate_capped_by_mpi(self):
        # Low MPI → gate further reduced below 0.8
        log = InterventionLog(physical_corrections=400)  # heavy intervention on 500 pts → MPI low
        manifest = _make_envelope(
            advisory_results=ADVISORY_WARN,
            intervention_log=log,
        ).build()
        gate = manifest["status"]["precondition_gate"]
        mpi = manifest["status"]["purity_index"]
        assert gate <= 0.8
        assert gate == round(min(0.8, mpi / 100.0), 4)


# ---------------------------------------------------------------------------
# MIF-UID
# ---------------------------------------------------------------------------


class TestMifUid:
    def test_mif_uid_starts_with_sha256(self):
        manifest = _make_envelope().build()
        assert manifest["mif_uid"].startswith("sha256:")

    def test_mif_uid_deterministic(self):
        env1 = _make_envelope()
        env2 = _make_envelope()
        assert env1.build()["mif_uid"] == env2.build()["mif_uid"]

    def test_mif_uid_changes_with_data_hash(self):
        uid1 = _make_envelope(raw_data_hash="sha256:aaa").build()["mif_uid"]
        uid2 = _make_envelope(raw_data_hash="sha256:bbb").build()["mif_uid"]
        assert uid1 != uid2

    def test_mif_uid_changes_with_calendar(self):
        uid1 = _make_envelope(calendar="NYSE").build()["mif_uid"]
        uid2 = _make_envelope(calendar="LSE").build()["mif_uid"]
        assert uid1 != uid2

    def test_mif_uid_changes_with_mode(self):
        uid1 = _make_envelope(mode=DQFMode.CERTIFICATION).build()["mif_uid"]
        uid2 = _make_envelope(mode=DQFMode.DIAGNOSTIC).build()["mif_uid"]
        assert uid1 != uid2

    def test_mif_uid_changes_with_version(self):
        uid1 = _make_envelope(dqf_version="1.1.0").build()["mif_uid"]
        uid2 = _make_envelope(dqf_version="1.2.0").build()["mif_uid"]
        assert uid1 != uid2


# ---------------------------------------------------------------------------
# to_json()
# ---------------------------------------------------------------------------


class TestToJson:
    def test_returns_valid_json(self):
        result = _make_envelope().to_json()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_round_trip(self):
        env = _make_envelope()
        manifest = env.build()
        parsed = json.loads(env.to_json())
        assert parsed["mif_uid"] == manifest["mif_uid"]
        assert parsed["status"]["overall"] == manifest["status"]["overall"]

    def test_json_contains_context(self):
        parsed = json.loads(_make_envelope().to_json())
        assert parsed["@context"] == "https://mif.dev/v1"


# ---------------------------------------------------------------------------
# Vitality helpers
# ---------------------------------------------------------------------------


class TestVitalityHelpers:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (100, "EXCELLENT"),
            (85, "EXCELLENT"),
            (84, "GOOD"),
            (60, "GOOD"),
            (59, "DEGRADED"),
            (35, "DEGRADED"),
            (34, "CRITICAL"),
            (0, "CRITICAL"),
        ],
    )
    def test_vitality_label_thresholds(self, score, expected):
        assert _vitality_label(score) == expected

    def test_void_status_vitality_score_is_zero(self):
        assert _mpi_to_vitality_score(95.0, STATUS_VOID) == 0

    def test_fail_status_vitality_score_is_10(self):
        from dqf.core.enums import STATUS_FAIL

        assert _mpi_to_vitality_score(95.0, STATUS_FAIL) == 10

    def test_certified_vitality_score_equals_int_mpi(self):
        assert _mpi_to_vitality_score(87.3, STATUS_CERTIFIED) == 87
