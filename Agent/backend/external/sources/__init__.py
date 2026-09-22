"""Data-source abstractions: where a step-2 snapshot payload comes from --
on-disk crawl output, or a direct live fetch -- kept separate per domain
(bot_source.py here; market_source.py owned by market/service.py's own
migration) so each stays a small, single-purpose seam.
"""

from Agent.backend.external.sources.bot_source import (
    BotDataSource,
    BotSourceError,
    FileBotDataSource,
    LiveBotDataSource,
)

__all__ = [
    "BotDataSource",
    "BotSourceError",
    "FileBotDataSource",
    "LiveBotDataSource",
]
