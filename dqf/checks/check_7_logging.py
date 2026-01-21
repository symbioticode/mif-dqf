"""
Check 7: Comprehensive Logging.

Records provenance and validation metadata.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from dqf.checks.base import BaseCheck, CheckResult
timestamp = datetime.now(timezone.utc).isoformat()


class ComprehensiveLoggingCheck(BaseCheck):
    """
    Check 7: Comprehensive Logging.

    Records:
    - Validation timestamp
    - Data provenance
    - Processing metadata
    - Configuration snapshot
    """

    def __init__(self):
        """Initialize Comprehensive Logging check."""
        super().__init__(check_id="check_7_logging", check_name="Comprehensive Logging")

    def run(
        self,
        data: pd.DataFrame,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> CheckResult:
        """
        Execute comprehensive logging.

        Args:
            data: DataFrame to validate
            symbol: Asset symbol
            source: Data source identifier
            metadata: Optional metadata dict
            **kwargs: Additional parameters:
                - save_provenance: bool (default: True)
                - provenance_dir: str (default: '_work/dqf/provenance')

        Returns:
            CheckResult with validation outcome
        """
        try:
            # Validate input
            self._validate_dataframe(data)

            # Extract config
            save_provenance = kwargs.get("save_provenance", True)
            provenance_dir = kwargs.get("provenance_dir", "_work/dqf/provenance")

            # Build provenance record
            timestamp = datetime.utcnow().isoformat()

            provenance = {
                "timestamp": timestamp,
                "symbol": symbol,
                "source": source,
                "metadata": metadata or {},
                "data_info": {
                    "row_count": len(data),
                    "columns": list(data.columns),
                    "start_date": (
                        str(data.index.min())
                        if isinstance(data.index, pd.DatetimeIndex)
                        else None
                    ),
                    "end_date": (
                        str(data.index.max())
                        if isinstance(data.index, pd.DatetimeIndex)
                        else None
                    ),
                    "has_timezone": (
                        data.index.tz is not None
                        if isinstance(data.index, pd.DatetimeIndex)
                        else False
                    ),
                },
                "validation_config": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["save_provenance", "provenance_dir"]
                },
            }

            # Add data statistics if available
            if "close" in data.columns:
                provenance["statistics"] = {
                    "close_mean": float(data["close"].mean()),
                    "close_std": float(data["close"].std()),
                    "close_min": float(data["close"].min()),
                    "close_max": float(data["close"].max()),
                }

            if "volume" in data.columns:
                if "statistics" not in provenance:
                    provenance["statistics"] = {}
                provenance["statistics"]["volume_mean"] = float(data["volume"].mean())
                provenance["statistics"]["volume_sum"] = float(data["volume"].sum())

            details = {
                "symbol": symbol,
                "source": source,
                "timestamp": timestamp,
                "provenance_saved": False,
                "provenance": provenance,  # Always include provenance dict
            }

            # Save provenance if requested
            if save_provenance:
                try:
                    prov_path = Path(provenance_dir)
                    prov_path.mkdir(parents=True, exist_ok=True)

                    # Create filename
                    safe_symbol = (
                        (symbol or "unknown").replace("/", "_").replace(":", "_")
                    )
                    filename = f"{safe_symbol}_{timestamp.replace(':', '-')}.json"
                    filepath = prov_path / filename

                    # Write provenance
                    with open(filepath, "w") as f:
                        json.dump(provenance, f, indent=2)

                    details["provenance_saved"] = True
                    details["saved"] = True  # Add 'saved' key for test compatibility
                    details["provenance_file"] = str(filepath)

                except Exception as e:
                    details["provenance_error"] = str(e)
                    details["saved"] = False  # Explicitly set to False on error
                    return self._create_warning_result(
                        message=f"Logging completed but provenance save failed: {str(e)}",
                        details=details,
                    )
            else:
                details["saved"] = False  # Explicitly set when not saving

            return self._create_pass_result(
                message="Comprehensive logging completed successfully",
                details=details,
            )

        except Exception as e:
            return self._create_error_result(
                message=f"Logging check failed: {str(e)}",
                exception=e,
            )
