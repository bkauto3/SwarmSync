"""
Discord Bot helper for Phase 9 dynamic channels.

This module is optional. It only activates when DISCORD_BOT_TOKEN and
DISCORD_GUILD_ID are configured. Otherwise the methods no-op so the rest
of the system can continue using webhooks.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

try:
    import discord
except ImportError:  # pragma: no cover - optional dependency
    discord = None  # type: ignore

logger = logging.getLogger(__name__)


class GenesisDiscordBot:
    """Minimal Discord client focused on per-business channels."""

    def __init__(self, *, guild_id: Optional[int] = None):
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.guild_id = guild_id or self._env_int("DISCORD_GUILD_ID")
        self.client: Optional["discord.Client"] = None
        self._ready_event: Optional[asyncio.Event] = None

    async def __aenter__(self) -> "GenesisDiscordBot":
        if not self._is_enabled():
            logger.info("Discord bot not configured; skipping Phase 9 features.")
            return self

        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True

        self.client = discord.Client(intents=intents)
        self._ready_event = asyncio.Event()

        @self.client.event
        async def on_ready():  # type: ignore
            logger.info("Discord bot connected as %s", self.client.user)  # pragma: no cover
            self._ready_event.set()

        asyncio.create_task(self.client.start(self.token))
        await self._ready_event.wait()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.client and self.client.is_ready():
            await self.client.close()
        self.client = None
        self._ready_event = None

    async def ensure_business_channel(self, business_id: str, business_name: str) -> Optional[int]:
        """Create or return the ID of the dynamic channel for a business."""
        client = await self._get_client()
        if not client:
            return None

        guild = await self._get_guild(client)
        if not guild:
            return None

        channel_name = f"business-{business_id.lower()}"
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return existing.id

        channel = await guild.create_text_channel(
            channel_name,
            topic=f"Autonomous build log for {business_name}",
            reason="Genesis Phase 9 dynamic channel",
        )
        return channel.id

    async def post_business_update(self, channel_id: int, message: str) -> None:
        client = await self._get_client()
        if not client:
            return
        channel = client.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(message[:1900])  # keep Discord limit in mind

    async def archive_channel(self, channel_id: int, *, reason: str = "Auto-archive") -> None:
        client = await self._get_client()
        if not client:
            return
        channel = client.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.edit(archived=True, reason=reason)

    async def _get_client(self) -> Optional["discord.Client"]:
        if not self._is_enabled():
            return None
        if not self.client or not self.client.is_ready():
            raise RuntimeError("Discord bot client is not ready. Use 'async with'.")
        return self.client

    async def _get_guild(self, client: "discord.Client") -> Optional["discord.Guild"]:
        if not self.guild_id:
            logger.warning("DISCORD_GUILD_ID not set; cannot manage dynamic channels.")
            return None
        guild = client.get_guild(self.guild_id)
        if not guild:
            guild = await client.fetch_guild(self.guild_id)
        return guild

    def _is_enabled(self) -> bool:
        return bool(self.token and discord is not None)

    @staticmethod
    def _env_int(key: str) -> Optional[int]:
        value = os.getenv(key)
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            logger.warning("Invalid int for %s: %s", key, value)
            return None

