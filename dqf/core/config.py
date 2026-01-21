"""
DQF Configuration Module.

Defines configuration structure for DQF validation framework.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class DQFConfig:
    """
    Configuration for DQF validation.

    Stores settings for all 7 checks and provides methods to load/save
    configurations from YAML files or dictionaries.
    """

    def __init__(self, **kwargs):
        """
        Initialize DQF configuration.

        Args:
            **kwargs: Optional check-specific configurations.
                     Format: check_1_source={'enabled': True, ...}

        Examples:
            >>> # Default config (all checks enabled)
            >>> config = DQFConfig()

            >>> # Custom config
            >>> config = DQFConfig(
            ...     check_2_integrity={'enabled': True, 'max_violation_rate': 0.01}
            ... )

            >>> # From YAML
            >>> config = DQFConfig.from_yaml("my_config.yaml")
        """
        # Default configuration for all 7 checks
        self.checks: Dict[str, Dict[str, Any]] = {
            "check_1_source": {
                "enabled": True,
                "require_metadata": False,
                "max_gap_days": 30,
            },
            "check_2_integrity": {
                "enabled": True,
                "max_violation_rate": 0.01,
                "required_columns": ["open", "high", "low", "close", "volume"],
            },
            "check_3_calendar": {
                "enabled": True,
                "auto_detect": True,
                "require_timezone": True,
            },
            "check_4_ffill": {
                "enabled": True,
                "max_consecutive_ffill": 3,
                "warn_threshold": 2,
                "columns_to_check": ["close"],
            },
            "check_5_trace": {
                "enabled": True,
                "require_unique": True,
                "require_chronological": True,
                "require_timezone": True,
            },
            "check_6_sanity": {
                "enabled": True,
                "extreme_return_threshold": 1.0,
                "zero_volume_days": 5,
                "volatility_multiplier": 5.0,
                "min_price": 1e-8,
            },
            "check_7_logging": {
                "enabled": True,
                "save_provenance": True,
                "provenance_dir": "_work/dqf/provenance",
            },
        }

        # Override defaults with provided kwargs
        for check_name, check_config in kwargs.items():
            if check_name in self.checks:
                # Merge with defaults (user config takes precedence)
                self.checks[check_name].update(check_config)
            else:
                # Unknown check name - store it anyway (for extensibility)
                self.checks[check_name] = check_config

    @classmethod
    def from_yaml(cls, filepath: str) -> "DQFConfig":
        """
        Load configuration from YAML file.

        Args:
            filepath: Path to YAML configuration file

        Returns:
            DQFConfig instance with loaded settings

        Example YAML:
            ```yaml
            check_1_source:
              enabled: true
              require_metadata: true
            check_2_integrity:
              enabled: true
              max_violation_rate: 0.02
            ```
        """
        filepath_obj = Path(filepath)

        if not filepath_obj.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath_obj, "r") as f:
            data = yaml.safe_load(f)

        # Extract checks dict if nested, otherwise use entire dict
        checks_data = data.get("checks", data)

        return cls(**checks_data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DQFConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Dictionary with check configurations

        Returns:
            DQFConfig instance
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {"checks": self.checks.copy()}

    def to_yaml(self, filepath: str) -> None:
        """
        Save configuration to YAML file.

        Args:
            filepath: Path where to save YAML configuration
        """
        filepath_obj = Path(filepath)
        filepath_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath_obj, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def get_enabled_checks(self) -> Dict[int, Dict[str, Any]]:
        """
        Get dictionary of enabled checks with their configs.

        Returns:
            Dict mapping check IDs (1-7) to their configurations.
            Only includes checks where 'enabled' is True.

        Example:
            >>> config = DQFConfig()
            >>> enabled = config.get_enabled_checks()
            >>> # {1: {...}, 2: {...}, 3: {...}, 4: {...}, 5: {...}, 6: {...}, 7: {...}}
        """
        enabled = {}

        for check_name, check_config in self.checks.items():
            # Extract check ID from name (e.g., "check_1_source" -> 1)
            if check_name.startswith("check_") and "_" in check_name[6:]:
                try:
                    check_id = int(check_name.split("_")[1])
                    if check_config.get("enabled", True):
                        enabled[check_id] = check_config
                except (ValueError, IndexError):
                    # Invalid check name format, skip
                    continue

        return enabled

    def is_check_enabled(self, check_id: int) -> bool:
        """
        Check if a specific check is enabled.

        Args:
            check_id: Check ID (1-7)

        Returns:
            True if check is enabled, False otherwise
        """
        check_name = f"check_{check_id}_"  # Partial match

        for name, config in self.checks.items():
            if name.startswith(check_name):
                return config.get("enabled", True)

        return False

    def get_check_config(self, check_id: int) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific check.

        Args:
            check_id: Check ID (1-7)

        Returns:
            Check configuration dict, or None if not found
        """
        check_name = f"check_{check_id}_"

        for name, config in self.checks.items():
            if name.startswith(check_name):
                return config.copy()

        return None

    def __repr__(self) -> str:
        """String representation of config."""
        enabled_count = sum(
            1 for cfg in self.checks.values() if cfg.get("enabled", True)
        )
        return f"DQFConfig(checks={len(self.checks)}, enabled={enabled_count})"
