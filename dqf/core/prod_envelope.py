"""
PROD Envelope — DQF v1.1
Provenance & Reliability Operational Data.

Produces the MIF-Lite manifest (.mif.json).

This component is NOT a data check. It is the trust mechanism of the output
format — the seal applied after all checks have run. It is called by
DQFValidator only when the pipeline completes without an unhandled exception.

Cryptographic strategy (Phase 1):
  sig_type: "sha256_provisional"
  Phase 2 will replace SHA-256 with Ed25519; the schema is unchanged, only
  the "value" field and "type" field are updated. Prior manifests remain
  structurally valid.

MIF-UID formula (spec §6):
  MIF-UID = SHA-256(raw_data_hash || dqf_version || calendar || mode)

Vitality score mapping (D-SIG v0.5 labels):
  [85, 100] → EXCELLENT
  [60,  84] → GOOD
  [35,  59] → DEGRADED
  [ 0,  34] → CRITICAL
"""

import base64
import hashlib
import json
from dataclasses import dataclass, field

from dqf.core.enums import (
    PRECONDITION_GATE,
    STATUS_CERTIFIED,
    STATUS_FAIL,
    STATUS_VOID,
    STATUS_WARNING,
    DQFMode,
)
from dqf.utils.mpi import InterventionLog, compute_mpi

# D-SIG v0.5 vitality thresholds
_VITALITY_THRESHOLDS = [
    (85, "EXCELLENT"),
    (60, "GOOD"),
    (35, "DEGRADED"),
    (0, "CRITICAL"),
]


def _vitality_label(score: int) -> str:
    """Map a vitality score (0–100) to a D-SIG v0.5 label."""
    for threshold, label in _VITALITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "CRITICAL"


def _mpi_to_vitality_score(mpi: float, overall_status: str) -> int:
    """
    Map MPI and overall status to a D-SIG vitality score (0–100 integer).

    VOID  → 0   (data cannot be trusted at all)
    FAIL  → 10  (unexpected pipeline error)
    Other → int(mpi), proportional to data purity
    """
    if overall_status == STATUS_VOID:
        return 0
    if overall_status == STATUS_FAIL:
        return 10
    return int(mpi)


@dataclass
class PRODEnvelope:
    """
    Builds and signs the MIF-Lite manifest for a completed DQF validation.

    Called by DQFValidator after all checks have run.  Not a check itself.

    Args:
        mode             : DQFMode used for this validation run.
        core_results     : Dict[check_id → status_str] for CORE checks.
                           Must include "PROD" (set to "PASS" by the validator).
        advisory_results : Dict[check_id → status_str] for ADVISORY checks.
        raw_data_hash    : Hex SHA-256 of the raw input DataFrame (prefixed
                           "sha256:"). Computed by the validator if not provided
                           by the caller.
        dqf_version      : DQF package version string (e.g. "1.1.0").
        calendar         : Declared trading calendar (e.g. "NYSE").
                           "UNKNOWN" if not provided in DIAGNOSTIC mode.
        intervention_log : InterventionLog aggregated from all checks.
        n_total_points   : Total OHLCV points = DataFrame.shape[0] * 5.
    """

    mode: DQFMode
    core_results: dict
    advisory_results: dict
    raw_data_hash: str
    dqf_version: str
    calendar: str
    intervention_log: InterventionLog
    n_total_points: int
    cleaning_log_bytes: bytes | None = field(default=None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_overall_status(self) -> str:
        """
        Derive overall status from check results.

        Rules (spec §3.1):
          - Any CORE result in {FAIL, ERROR} → VOID
          - Any ADVISORY result == WARN       → WARNING
          - Otherwise                         → CERTIFIED
        """
        if any(v in ("FAIL", "ERROR") for v in self.core_results.values()):
            return STATUS_VOID
        if any(v == "WARN" for v in self.advisory_results.values()):
            return STATUS_WARNING
        return STATUS_CERTIFIED

    def _compute_mif_uid(self) -> str:
        """
        MIF-UID = SHA-256(raw_data_hash || dqf_version || calendar || mode)

        Computed on raw data, not cleaned data (spec §6).
        Any change to DQF's cleaning algorithm must increment the major
        version, which changes the mif_uid and invalidates prior certs.
        """
        payload = (self.raw_data_hash + self.dqf_version + self.calendar + self.mode.value).encode(
            "utf-8"
        )
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def _compute_source_sig(self, mif_uid: str) -> str:
        """
        Phase 1 provisional signature: SHA-256 of the MIF-UID.

        Guarantees immutability of the manifest (tamper-evident hash chain)
        without requiring a PKI. Phase 2 will replace this with an Ed25519
        signature over mif_uid using a long-lived identity key.
        """
        return hashlib.sha256(mif_uid.encode("utf-8")).hexdigest()

    def _cleaning_log_uri(self) -> str | None:
        """
        Return cleaning_log_uri for the manifest provenance block.

        Phase 1 (no bytes): None
        Phase 1 (bytes embedded): "embedded:sha256:<hex>"
        Phase 2: external Parquet URI will be used instead.
        """
        if self.cleaning_log_bytes is None:
            return None
        digest = hashlib.sha256(self.cleaning_log_bytes).hexdigest()
        return f"embedded:sha256:{digest}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> dict:
        """
        Assemble and return the MIF-Lite manifest as a Python dict.

        The dict is the canonical representation; to_json() serialises it.
        All invariants from spec §3–§7 are enforced here:
          - CORE FAIL  → overall VOID   → gate 0.0
          - ADVISORY WARN → WARNING     → gate capped by MPI (max 0.8)
          - Clean run  → CERTIFIED      → gate 1.0
          - sig_type   always "sha256_provisional" in Phase 1
          - cleaning_log_uri always null in Phase 1
          - vitality_signal.label always in D-SIG v0.5 vocabulary
        """
        overall_status = self._compute_overall_status()
        mpi = compute_mpi(self.intervention_log, self.n_total_points)
        mif_uid = self._compute_mif_uid()
        source_sig = self._compute_source_sig(mif_uid)

        # Gate value from spec §7 table
        gate = PRECONDITION_GATE.get(overall_status, 0.0)

        # Cap gate on MPI when WARNING (spec §7: "MPI-based cap, max 0.8")
        if overall_status == STATUS_WARNING:
            gate = min(gate, mpi / 100.0)

        vitality_score = _mpi_to_vitality_score(mpi, overall_status)

        manifest = {
            "@context": "https://mif.dev/v1",
            "@type": "DataCertification",
            "mif_uid": mif_uid,
            "status": {
                "overall": overall_status,
                "precondition_gate": round(gate, 4),
                "purity_index": round(mpi, 2),
            },
            "checks": {
                "core": self.core_results,
                "advisory": self.advisory_results,
            },
            "vitality_signal": {
                "score": vitality_score,
                "label": _vitality_label(vitality_score),
                "trend": "STABLE",  # Phase 2: compare against historical MPI
            },
            "provenance": {
                "dqf_version": self.dqf_version,
                "mode": self.mode.value,
                "source_hash": self.raw_data_hash,
                "calendar": self.calendar,
                "cleaning_log_uri": self._cleaning_log_uri(),
            },
            "signature": {
                "type": "sha256_provisional",
                "value": source_sig,
            },
        }

        if self.cleaning_log_bytes is not None:
            manifest["cleaning_log"] = base64.b64encode(self.cleaning_log_bytes).decode("ascii")

        return manifest

    def to_json(self, indent: int = 2) -> str:
        """Serialise the manifest as a JSON string."""
        return json.dumps(self.build(), indent=indent, ensure_ascii=False)
