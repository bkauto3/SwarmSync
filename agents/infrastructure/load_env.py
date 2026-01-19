"""
Auto-load .env file for Genesis infrastructure

This module automatically loads environment variables from .env
when any Genesis module is imported. Place this import at the top
of entry point files to ensure configuration is loaded.

Usage:
    from infrastructure.load_env import load_genesis_env
    load_genesis_env()  # Loads .env if exists
"""

import os
from pathlib import Path
from typing import Iterable, Set

_ENV_LOADED = False


def load_genesis_env(env_file: str = ".env", override: bool = False):
    """
    Load environment variables from .env file
    
    Args:
        env_file: Path to .env file (default: ".env" in project root)
        override: Whether to override existing environment variables
    
    Returns:
        Number of variables loaded
    """
    global _ENV_LOADED
    
    if _ENV_LOADED and not override:
        return 0  # Already loaded, skip
    
    project_root = Path(__file__).parent.parent.parent  # infrastructure/ -> agents/ -> Agent-Market/

    if env_file != ".env":
        candidates: Iterable[Path] = [project_root / env_file]
    else:
        candidates = [
            project_root / ".env",
            project_root / ".env.local",
            project_root / ".env.genesis.secrets",
        ]

    visited: Set[Path] = set()
    total_loaded = 0
    for candidate in candidates:
        total_loaded += _load_env_file(candidate, override=override, visited=visited)

    _ENV_LOADED = True
    return total_loaded


def _load_env_file(env_path: Path, override: bool, visited: Set[Path]) -> int:
    if env_path in visited:
        return 0
    visited.add(env_path)

    if not env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path, override=override)
        except ImportError:
            pass
        return 0

    loaded_count = 0
    try:
        with open(env_path, "r") as handle:
            for raw_line in handle:
                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("source ") or line.startswith(". "):
                    _, include_path = line.split(None, 1)
                    include_file = (env_path.parent / include_path).resolve()
                    loaded_count += _load_env_file(include_file, override=override, visited=visited)
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    if "#" in value:
                        value = value.split("#", 1)[0].strip()

                    if override or key not in os.environ:
                        os.environ[key] = value
                        loaded_count += 1

    except Exception as exc:
        print(f"Warning: Could not load env file {env_path}: {exc}")

    return loaded_count


# Auto-load on import (convenient for infrastructure modules)
load_genesis_env()

