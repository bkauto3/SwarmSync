"""
Utility helpers for persisting and retrieving WaltzRL DIR reports.

The WaltzRL safety evaluations write a consolidated DIR report to disk so the
orchestration layer (AOPValidator) can enforce continuous improvement
thresholds.  This module provides a tiny wrapper around that file so callers
can load the most recent report without needing to know the storage path.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_DIR_REPORT_PATH = Path(
    os.getenv("WALTZRL_DIR_REPORT_PATH", "data/waltzrl/latest_dir_report.json")
)


def ensure_directory(path: Path) -> None:
    """Ensure the parent directory for ``path`` exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def save_dir_report(report: Dict[str, Any], path: Optional[Path] = None) -> Path:
    """
    Persist a DIR report to disk.

    Args:
        report: DIR report dictionary produced by ``generate_dir_report``.
        path: Optional custom path. Defaults to ``DEFAULT_DIR_REPORT_PATH``.

    Returns:
        Path where the report was written.
    """
    target_path = path or DEFAULT_DIR_REPORT_PATH
    ensure_directory(target_path)

    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)

    logger.debug("Saved DIR report", extra={"path": str(target_path)})
    return target_path


def load_latest_dir_report(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load the most recent DIR report if one is available.

    Args:
        path: Optional custom path. Defaults to ``DEFAULT_DIR_REPORT_PATH``.

    Returns:
        Parsed report dictionary, or ``None`` if the file is missing or invalid.
    """
    target_path = path or DEFAULT_DIR_REPORT_PATH

    if not target_path.exists():
        logger.debug("DIR report not found", extra={"path": str(target_path)})
        return None

    try:
        with target_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to decode DIR report; ignoring file",
            extra={"path": str(target_path), "error": str(exc)},
        )
        return None

    if not isinstance(report, dict):
        logger.warning(
            "DIR report has unexpected structure; ignoring file",
            extra={"path": str(target_path)},
        )
        return None

    return report
