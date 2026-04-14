"""
MIF Purity Index (MPI) — DQF v1.1

Measures how much DQF had to intervene to produce the certified canonical
dataset. A score of 100 means zero intervention; the raw data was already
canonical.

Formula (spec §5):
    MPI = 100 × (1 - Σ(interventions_i × gravity_i) / N_total_points)

Gravity weights:
    physical_correction : 1.0  (H < L corrected, NaN in OHLC replaced, etc.)
    forward_fill        : 0.5  (missing bar interpolated via forward-fill)
    calendar_removal    : 0.2  (bar removed because outside declared calendar)

N_total_points = DataFrame.shape[0] × 5  (rows × OHLCV columns)
"""

from dataclasses import dataclass

GRAVITY: dict[str, float] = {
    "physical_correction": 1.0,
    "forward_fill": 0.5,
    "calendar_removal": 0.2,
}

VALID_INTERVENTION_TYPES = frozenset(GRAVITY.keys())


@dataclass
class InterventionLog:
    """
    Accumulates intervention counts emitted by each DQF check.

    Each check that modifies data must call ``add()`` once per intervention
    type so the MPI can be computed at the end of the pipeline.

    Attributes:
        physical_corrections: Count of physical law violations corrected
            (e.g. H < L fixed, NaN in OHLCV filled). Gravity 1.0.
        forward_fills: Count of consecutive forward-fill sequences applied
            to recover missing bars. Gravity 0.5.
        calendar_removals: Count of bars removed because they fall outside
            the declared trading calendar. Gravity 0.2.
    """

    physical_corrections: int = 0
    forward_fills: int = 0
    calendar_removals: int = 0

    def add(self, intervention_type: str, count: int = 1) -> None:
        """
        Record ``count`` interventions of the given type.

        Args:
            intervention_type: One of 'physical_correction', 'forward_fill',
                or 'calendar_removal'.
            count: Number of interventions to add (must be >= 0).

        Raises:
            ValueError: If ``intervention_type`` is unknown or ``count`` < 0.
        """
        if count < 0:
            raise ValueError(f"Intervention count must be >= 0, got {count}")
        if intervention_type == "physical_correction":
            self.physical_corrections += count
        elif intervention_type == "forward_fill":
            self.forward_fills += count
        elif intervention_type == "calendar_removal":
            self.calendar_removals += count
        else:
            raise ValueError(
                f"Unknown intervention type: {intervention_type!r}. "
                f"Valid types: {sorted(VALID_INTERVENTION_TYPES)}"
            )

    def total_weighted(self) -> float:
        """
        Return the sum of (count × gravity) across all intervention types.

        A value of 0.0 means no interventions were recorded.
        """
        return (
            self.physical_corrections * GRAVITY["physical_correction"]
            + self.forward_fills * GRAVITY["forward_fill"]
            + self.calendar_removals * GRAVITY["calendar_removal"]
        )

    def total_count(self) -> int:
        """Return the raw (unweighted) total number of interventions."""
        return self.physical_corrections + self.forward_fills + self.calendar_removals

    def __add__(self, other: "InterventionLog") -> "InterventionLog":
        """Merge two logs — used by the validator to aggregate across checks."""
        if not isinstance(other, InterventionLog):
            return NotImplemented
        return InterventionLog(
            physical_corrections=self.physical_corrections + other.physical_corrections,
            forward_fills=self.forward_fills + other.forward_fills,
            calendar_removals=self.calendar_removals + other.calendar_removals,
        )

    def __repr__(self) -> str:
        return (
            f"InterventionLog("
            f"physical={self.physical_corrections}, "
            f"ffill={self.forward_fills}, "
            f"calendar={self.calendar_removals}, "
            f"weighted={self.total_weighted():.2f})"
        )


def compute_mpi(log: InterventionLog, n_total_points: int) -> float:
    """
    Compute the MIF Purity Index for a validated dataset.

    MPI = 100 × (1 − Σ(interventions_i × gravity_i) / N_total_points)

    The result is clamped to [0.0, 100.0].

    Args:
        log: InterventionLog aggregated from all checks in the pipeline.
        n_total_points: Total number of OHLCV data points in the dataset.
            Should be ``DataFrame.shape[0] * 5`` (rows × 5 OHLCV columns).

    Returns:
        MPI score as a float in [0.0, 100.0].
        100.0 means zero intervention — raw data was already canonical.

    Raises:
        ValueError: If ``n_total_points`` <= 0.

    Examples:
        >>> log = InterventionLog()
        >>> compute_mpi(log, 1000)
        100.0

        >>> log = InterventionLog(physical_corrections=2)
        >>> compute_mpi(log, 1000)  # 2 × 1.0 / 1000 = 0.2% cost
        99.8
    """
    if n_total_points <= 0:
        raise ValueError(f"n_total_points must be > 0, got {n_total_points}")

    weighted = log.total_weighted()
    raw = 100.0 * (1.0 - weighted / n_total_points)
    return max(0.0, min(100.0, raw))
