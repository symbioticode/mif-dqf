"""
DQF Validator — v1.1

Orchestrates the DQF pipeline:
  1. Run CORE checks (C2, C3, C5) and ADVISORY checks (C1 if enabled, C4).
  2. Aggregate InterventionLog across all checks for MPI computation.
  3. Inject PROD = "PASS" into core_results (envelope seal).
  4. Build the MIF-Lite manifest via PRODEnvelope.
  5. Return a DQFReport wrapping the manifest.

Design constraints (spec §3):
  - CORE checks run unconditionally in CERTIFICATION mode. A FAIL on any
    CORE check propagates to STATUS_VOID in the manifest and gate = 0.0.
  - ADVISORY checks produce STATUS_WARNING in the manifest when they WARN,
    but never block certification.
  - C1 is SKIP in Phase 1 (DAL not yet connected).
  - C6 and C7 have been removed (see spec §8).
"""

import hashlib
import logging

import pandas as pd

from dqf.checks.base import CheckResult
from dqf.checks.check_2_integrity import IntegrityCheck
from dqf.checks.check_3_calendar import CalendarAlignmentCheck
from dqf.checks.check_4_ffill import ForwardFillCheck
from dqf.checks.check_5_trace import IndexTraceabilityCheck
from dqf.core.config import DQFConfig
from dqf.core.enums import (
    SEVERITY_CRITICAL,
    STATUS_ERROR,
    STATUS_SKIP,
)
from dqf.core.prod_envelope import PRODEnvelope
from dqf.core.report import DQFReport
from dqf.utils import cleaning_log as _cleaning_log
from dqf.utils.mpi import InterventionLog

# DQF spec version — increment with any change to CORE check logic (spec §6)
DQF_VERSION = "1.2.0"

logger = logging.getLogger(__name__)


class DQFValidator:
    """
    DQF v1.1 validation orchestrator.

    Usage::

        config = DQFConfig(mode=DQFMode.CERTIFICATION)
        validator = DQFValidator(config)
        report = validator.validate(df, calendar="NYSE")

        if report.is_certified:
            print(f"MPI: {report.purity_index:.1f}")
        else:
            print(f"Status: {report.overall_status}, gate={report.precondition_gate}")
    """

    # CORE checks: failure → overall status VOID, precondition_gate = 0.0
    CORE_CHECKS: frozenset[str] = frozenset({"PROD", "C2", "C3", "C5"})
    # ADVISORY checks: WARN → overall status WARNING, gate capped by MPI
    ADVISORY_CHECKS: frozenset[str] = frozenset({"C1", "C4"})

    def __init__(self, config: DQFConfig) -> None:
        """
        Initialise the validator.

        Args:
            config: DQFConfig instance. The ``mode`` field is mandatory;
                    DQFConfig.__post_init__ raises TypeError if absent.

        Raises:
            TypeError: If ``config`` is not a DQFConfig instance.
        """
        if not isinstance(config, DQFConfig):
            raise TypeError(f"config must be a DQFConfig instance, got {type(config).__name__!r}")
        self.config = config
        self._init_checks()
        logger.info(
            "DQFValidator v%s initialised — mode=%s, checks=%s",
            DQF_VERSION,
            config.mode.value,
            sorted(self._checks.keys()),
        )

    def _init_checks(self) -> None:
        """Instantiate checks according to config."""
        self._checks: dict[str, object] = {
            "C2": IntegrityCheck(),
            "C3": CalendarAlignmentCheck(),
            "C5": IndexTraceabilityCheck(),
            "C4": ForwardFillCheck(),
        }
        # C1: ADVISORY, active only when DAL is connected (Phase 2+)
        if self.config.c1_enabled:
            from dqf.checks.check_1_source import SourceUniquenessCheck

            self._checks["C1"] = SourceUniquenessCheck()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        df: pd.DataFrame,
        calendar: str | None = None,
        raw_data_hash: str | None = None,
        enable_cleaning_log: bool = False,
    ) -> DQFReport:
        """
        Run the full DQF validation pipeline.

        Args:
            df                 : OHLCV DataFrame to validate.
            calendar           : Declared trading calendar (e.g. "NYSE"). Required
                                 in CERTIFICATION mode; optional in DIAGNOSTIC.
            raw_data_hash      : SHA-256 of the raw input data (hex string, prefixed
                                 "sha256:"). Computed from ``df`` if not provided.
                                 Callers should provide this when they hold the
                                 original bytes (e.g. from a DAL handoff), so the
                                 hash reflects the source, not the in-memory copy.
            enable_cleaning_log: When True, aggregate per-row intervention entries
                                 from all checks and embed a Parquet cleaning log
                                 in the manifest (v1.2). Default False.

        Returns:
            DQFReport wrapping the MIF-Lite manifest.

        Raises:
            TypeError: If ``df`` is not a pandas DataFrame.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"df must be a pandas DataFrame, got {type(df).__name__!r}")

        if raw_data_hash is None:
            raw_data_hash = self._hash_dataframe(df)

        core_results: dict[str, str] = {}
        advisory_results: dict[str, str] = {}
        aggregated_log = InterventionLog()
        all_cleaning_entries: list[dict] = []

        # ------------------------------------------------------------------
        # Run checks
        # ------------------------------------------------------------------
        for check_id, check in self._checks.items():
            try:
                result: CheckResult = check.run(
                    data=df,
                    mode=self.config.mode,
                    calendar=calendar,
                    config=self.config,
                    # C4 thresholds from config
                    max_consecutive_ffill=self.config.c4_max_consecutive_ffill,
                    warn_threshold=self.config.c4_warn_threshold,
                )
            except Exception as exc:
                logger.error("Check %s raised an unexpected exception: %s", check_id, exc)
                result = CheckResult(
                    check_name=check_id,
                    status=STATUS_ERROR,
                    severity=SEVERITY_CRITICAL,
                    message=f"Check {check_id} crashed: {exc}",
                )

            # Aggregate interventions for MPI
            if result.interventions is not None:
                aggregated_log = aggregated_log + result.interventions

            # Aggregate cleaning entries (v1.2)
            if enable_cleaning_log and result.cleaning_entries:
                all_cleaning_entries.extend(result.cleaning_entries)

            # Route to CORE or ADVISORY bucket
            if check_id in self.CORE_CHECKS:
                core_results[check_id] = result.status
            else:
                advisory_results[check_id] = result.status

        # ------------------------------------------------------------------
        # PROD seal — envelope succeeds iff no unhandled crash above
        # (spec §4: "not a data check — it is the output format's trust mechanism")
        # ------------------------------------------------------------------
        core_results["PROD"] = "PASS"

        # C1 not in Phase 1 → explicit SKIP
        if "C1" not in advisory_results:
            advisory_results["C1"] = STATUS_SKIP

        # ------------------------------------------------------------------
        # MIF-Lite manifest
        # ------------------------------------------------------------------
        n_total_points = max(df.shape[0] * 5, 1)  # rows × OHLCV columns

        # Serialise cleaning log if requested
        cleaning_log_bytes = (
            _cleaning_log.to_parquet(all_cleaning_entries) if enable_cleaning_log else None
        )

        envelope = PRODEnvelope(
            mode=self.config.mode,
            core_results=core_results,
            advisory_results=advisory_results,
            raw_data_hash=raw_data_hash,
            dqf_version=DQF_VERSION,
            calendar=calendar or "UNKNOWN",
            intervention_log=aggregated_log,
            n_total_points=n_total_points,
            cleaning_log_bytes=cleaning_log_bytes,
        )
        manifest = envelope.build()

        logger.info(
            "Validation complete — status=%s, mpi=%.1f, gate=%s",
            manifest["status"]["overall"],
            manifest["status"]["purity_index"],
            manifest["status"]["precondition_gate"],
        )

        return DQFReport(manifest=manifest, cleaned_data=df)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_dataframe(df: pd.DataFrame) -> str:
        """
        Compute a deterministic SHA-256 over the DataFrame content.

        Uses pandas' internal hash (includes index and all columns).
        Result is prefixed with "sha256:" for manifest compatibility.
        """
        raw_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return "sha256:" + hashlib.sha256(raw_bytes).hexdigest()

    def __repr__(self) -> str:
        return (
            f"DQFValidator(mode={self.config.mode.value!r}, "
            f"checks={sorted(self._checks.keys())})"
        )
