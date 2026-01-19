from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Union

from infrastructure.hopx_client import HopXClient, HopXCommandResult, run_sync
from infrastructure.genesis_discord import GenesisDiscord

FilePayload = Union[str, bytes, Dict[str, "FilePayload"]]


def collect_directory_payload(
    root: Union[str, Path],
    *,
    max_bytes: int = 15_000_000,
    ignore_hidden: bool = True,
) -> Dict[str, bytes]:
    """Serialize a directory tree for HopX uploads."""

    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    payload: Dict[str, bytes] = {}
    total_bytes = 0

    for file_path in root_path.rglob("*"):
        if file_path.is_dir():
            continue
        rel = file_path.relative_to(root_path).as_posix()
        if ignore_hidden and any(part.startswith(".") for part in file_path.relative_to(root_path).parts):
            continue
        data = file_path.read_bytes()
        total_bytes += len(data)
        if total_bytes > max_bytes:
            raise ValueError(
                f"Directory {root_path} exceeds HopX max_bytes limit ({max_bytes} bytes)"
            )
        payload[rel] = data

    if not payload:
        raise ValueError(f"No files found in {root_path}")
    return payload


def _is_enabled() -> bool:
    return os.getenv("HOPX_ENABLED", "true").lower() in {"1", "true", "yes"}


class HopXAgentAdapter:
    """Utility class that ties HopXClient and GenesisDiscord together."""

    def __init__(self, agent_name: str, business_id: str):
        self.agent_name = agent_name
        self.business_id = business_id
        self.enabled = _is_enabled()
        self.client = HopXClient()

    async def execute(
        self,
        *,
        task: str,
        template: str,
        upload_files: Optional[Dict[str, object]] = None,
        commands: Optional[Sequence[str]] = None,
        download_paths: Optional[Iterable[str]] = None,
    ) -> Optional[Dict]:
        if not self.enabled:
            return None

        discord = GenesisDiscord()
        await discord.agent_started(self.business_id, self.agent_name, task)

        env = await self.client.create_environment(self.business_id, template=template)
        command_results = []
        artifacts = {}

        try:
            if upload_files:
                self.client.upload_files(env.env_id, upload_files)

            for command in commands or []:
                await discord.agent_progress(
                    self.business_id, self.agent_name, f"Running `{command}`"
                )
                result: HopXCommandResult = await self.client.execute_command(
                    env.env_id, command
                )
                command_results.append(result.__dict__)
                if not result.success:
                    raise RuntimeError(result.stderr or f"Command failed: {command}")

            if download_paths:
                artifacts = await self.client.download_results(env.env_id, download_paths)

            await discord.agent_completed(
                self.business_id, self.agent_name, f"{task} completed in HopX"
            )
            return {"commands": command_results, "artifacts": artifacts}

        except Exception as exc:
            await discord.agent_error(self.business_id, self.agent_name, str(exc))
            raise

        finally:
            await self.client.destroy_environment(env.env_id)
            await discord.close()

    def execute_sync(self, **kwargs) -> Optional[Dict]:
        return run_sync(self.execute(**kwargs))

