"""
DQF Report Module — v1.1

DQFReport is a thin, read-only wrapper around the MIF-Lite manifest produced
by PRODEnvelope. The manifest is the single source of truth; all properties
are accessors on it.

No mutable state is introduced after construction. Serialisation methods
(to_json, to_yaml) reproduce the manifest verbatim.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
import yaml

from dqf.core.enums import STATUS_CERTIFIED


@dataclass
class DQFReport:
    """
    Result of a DQF v1.1 validation run.

    The ``manifest`` dict is the canonical .mif.json artefact produced by
    PRODEnvelope. All public properties delegate to it so callers never need
    to navigate the dict directly.

    ``cleaned_data`` is the DataFrame that was validated. In Phase 1, DQF
    does not actively clean data (it detects and reports); Phase 2 will
    replace or supplement this field with the actively cleaned version.

    Args:
        manifest     : MIF-Lite dict from PRODEnvelope.build().
        cleaned_data : The validated DataFrame (passthrough in Phase 1).
    """

    manifest: dict[str, Any]
    cleaned_data: pd.DataFrame

    # ------------------------------------------------------------------
    # Status accessors
    # ------------------------------------------------------------------

    @property
    def overall_status(self) -> str:
        """One of: CERTIFIED, WARNING, VOID, FAIL."""
        return cast(str, self.manifest["status"]["overall"])

    @property
    def precondition_gate(self) -> float:
        """
        Gate value applied to downstream MIF scores (spec §7).

        1.0 = CERTIFIED, 0.8 = WARNING (MPI-capped), 0.2 = FAIL, 0.0 = VOID.
        """
        return cast(float, self.manifest["status"]["precondition_gate"])

    @property
    def purity_index(self) -> float:
        """MIF Purity Index in [0.0, 100.0]. 100.0 = zero intervention."""
        return cast(float, self.manifest["status"]["purity_index"])

    @property
    def is_certified(self) -> bool:
        """True only when overall_status == CERTIFIED."""
        return self.overall_status == STATUS_CERTIFIED

    # ------------------------------------------------------------------
    # Identity accessors
    # ------------------------------------------------------------------

    @property
    def mif_uid(self) -> str:
        """Unique certification identifier (sha256-prefixed hex digest)."""
        return cast(str, self.manifest["mif_uid"])

    @property
    def dqf_version(self) -> str:
        return cast(str, self.manifest["provenance"]["dqf_version"])

    @property
    def mode(self) -> str:
        """Validation mode as string: 'CERTIFICATION' or 'DIAGNOSTIC'."""
        return cast(str, self.manifest["provenance"]["mode"])

    @property
    def calendar(self) -> str:
        return cast(str, self.manifest["provenance"]["calendar"])

    # ------------------------------------------------------------------
    # Check result accessors
    # ------------------------------------------------------------------

    @property
    def core_results(self) -> dict[str, Any]:
        """Dict[check_id → status_str] for CORE checks."""
        return cast(dict[str, Any], self.manifest["checks"]["core"])

    @property
    def advisory_results(self) -> dict[str, Any]:
        """Dict[check_id → status_str] for ADVISORY checks."""
        return cast(dict[str, Any], self.manifest["checks"]["advisory"])

    # ------------------------------------------------------------------
    # Vitality signal
    # ------------------------------------------------------------------

    @property
    def vitality_score(self) -> int:
        return cast(int, self.manifest["vitality_signal"]["score"])

    @property
    def vitality_label(self) -> str:
        """D-SIG v0.5 label: EXCELLENT, GOOD, DEGRADED, or CRITICAL."""
        return cast(str, self.manifest["vitality_signal"]["label"])

    # ------------------------------------------------------------------
    # Cleaning log (v1.2)
    # ------------------------------------------------------------------

    @property
    def has_cleaning_log(self) -> bool:
        """True when the manifest embeds a cleaning log (enable_cleaning_log=True was used)."""
        return "cleaning_log" in self.manifest

    def get_cleaning_log_df(self) -> pd.DataFrame | None:
        """
        Decode and return the embedded cleaning log as a DataFrame.

        Returns:
            DataFrame with columns row_index, check_id, intervention, field,
            value_before, value_after, gravity — or None if no log is embedded.
        """
        if not self.has_cleaning_log:
            return None
        from dqf.utils import cleaning_log as _cl  # local import to avoid circular deps

        raw_bytes = base64.b64decode(self.manifest["cleaning_log"])
        return _cl.from_parquet(raw_bytes)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Return the MIF-Lite manifest as a JSON string."""
        return json.dumps(self.manifest, indent=indent, ensure_ascii=False)

    def to_yaml(self) -> str:
        """Return the MIF-Lite manifest as a YAML string."""
        return yaml.dump(self.manifest, default_flow_style=False, allow_unicode=True)

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def print_summary(self) -> None:
        """Print a compact, human-readable validation summary."""
        s = self.manifest["status"]
        v = self.manifest["vitality_signal"]
        p = self.manifest["provenance"]
        sig = self.manifest["signature"]

        print("=" * 60)
        print(f"DQF v{p['dqf_version']} — {p['mode']}")
        print("=" * 60)
        print(f"  Status   : {s['overall']}")
        print(f"  MPI      : {s['purity_index']:.1f}/100")
        print(f"  Gate     : {s['precondition_gate']}")
        print(f"  Vitality : {v['label']} ({v['score']}) — {v['trend']}")
        print(f"  Calendar : {p['calendar']}")
        print(f"  UID      : {self.mif_uid[:48]}...")
        print(f"  Sig type : {sig['type']}")
        print()
        print("  CORE checks:")
        for check_id, status in self.core_results.items():
            icon = "" if status == "PASS" else "" if status == "SKIP" else ""
            print(f"    {icon} {check_id}: {status}")
        print("  ADVISORY checks:")
        for check_id, status in self.advisory_results.items():
            icon = "" if status in ("PASS", "SKIP") else ""
            print(f"    {icon} {check_id}: {status}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"DQFReport(status={self.overall_status!r}, "
            f"mpi={self.purity_index:.1f}, "
            f"gate={self.precondition_gate})"
        )
