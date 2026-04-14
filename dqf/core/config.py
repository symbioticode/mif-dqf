"""
DQF Configuration Module — v1.1

DQFConfig requires an explicit operational mode (DQFMode).
There is no default — callers must declare intent.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from dqf.core.enums import DQFMode


@dataclass
class DQFConfig:
    """
    Configuration for DQF v1.1 validation.

    The ``mode`` parameter is MANDATORY. There is no default.

    CERTIFICATION : CORE checks are active and non-bypassable. Calendar must
                    be explicitly declared in the ``validate()`` call.
    DIAGNOSTIC    : ADVISORY checks are configurable. Calendar auto-detection
                    is permitted.

    Args:
        mode: DQFMode.CERTIFICATION or DQFMode.DIAGNOSTIC.

        c4_max_consecutive_ffill: Maximum consecutive forward-filled bars before
            C4 raises FAIL (default: 3). Recorded as metadata in CERTIFICATION.
        c4_warn_threshold: Number of consecutive ffill bars that triggers a WARN
            before hitting the hard limit (default: 2).

        c1_enabled: Whether to run C1 (Stream Integrity). False in Phase 1
            because DAL is not yet connected. When True, C1 is ADVISORY.

    Examples:
        >>> config = DQFConfig(mode=DQFMode.CERTIFICATION)
        >>> config = DQFConfig(mode=DQFMode.DIAGNOSTIC, c4_max_consecutive_ffill=5)
        >>> config = DQFConfig.from_yaml("dqf_config.yaml")
    """

    mode: DQFMode

    # C4 — Forward-Fill Limits (ADVISORY)
    c4_max_consecutive_ffill: int = 3
    c4_warn_threshold: int = 2

    # C1 — Stream Integrity (ADVISORY, DAL-pending)
    # Phase 1: always False. Set True once DAL is connected.
    c1_enabled: bool = False  # DAL-pending

    def __post_init__(self) -> None:
        if not isinstance(self.mode, DQFMode):
            raise TypeError(
                f"mode must be DQFMode.CERTIFICATION or DQFMode.DIAGNOSTIC, "
                f"got {type(self.mode).__name__!r}"
            )
        if self.c4_max_consecutive_ffill < 1:
            raise ValueError(
                f"c4_max_consecutive_ffill must be >= 1, " f"got {self.c4_max_consecutive_ffill}"
            )
        if self.c4_warn_threshold < 1:
            raise ValueError(f"c4_warn_threshold must be >= 1, " f"got {self.c4_warn_threshold}")
        if self.c4_warn_threshold >= self.c4_max_consecutive_ffill:
            raise ValueError(
                f"c4_warn_threshold ({self.c4_warn_threshold}) must be "
                f"< c4_max_consecutive_ffill ({self.c4_max_consecutive_ffill})"
            )

    @classmethod
    def from_yaml(cls, path: str) -> "DQFConfig":
        """
        Load configuration from a YAML file.

        The YAML file must declare a ``mode`` key with value CERTIFICATION or
        DIAGNOSTIC. All other keys are optional and fall back to defaults.

        Example YAML::

            mode: CERTIFICATION
            c4_max_consecutive_ffill: 3
            c4_warn_threshold: 2
            c1_enabled: false

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If ``mode`` is missing or has an invalid value.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"DQF config file not found: {path}")

        with open(filepath) as f:
            data = yaml.safe_load(f) or {}

        mode_str = data.pop("mode", None)
        if mode_str is None:
            raise ValueError(f"DQF config '{path}' must declare 'mode: CERTIFICATION|DIAGNOSTIC'")
        try:
            data["mode"] = DQFMode(mode_str)
        except ValueError as err:
            raise ValueError(
                f"Invalid mode '{mode_str}' in '{path}'. "
                f"Accepted values: CERTIFICATION, DIAGNOSTIC"
            ) from err

        return cls(**data)

    def to_dict(self) -> dict:
        """Export configuration as a plain dictionary."""
        return {
            "mode": self.mode.value,
            "c4_max_consecutive_ffill": self.c4_max_consecutive_ffill,
            "c4_warn_threshold": self.c4_warn_threshold,
            "c1_enabled": self.c1_enabled,
        }

    def to_yaml(self, path: str) -> None:
        """Save configuration to a YAML file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def __repr__(self) -> str:
        return (
            f"DQFConfig(mode={self.mode.value!r}, "
            f"c4_max_consecutive_ffill={self.c4_max_consecutive_ffill}, "
            f"c4_warn_threshold={self.c4_warn_threshold}, "
            f"c1_enabled={self.c1_enabled})"
        )
