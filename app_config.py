import os
from typing import Optional
from dotenv import load_dotenv
import json


class Config:
    def __init__(self) -> None:
        load_dotenv(verbose=True)
        self.bot_token: str = os.environ.get("BOT_TOKEN")
        self.guild_ids: Optional[list[str]] = json.loads(os.environ.get("GUILD_IDS", "[]"))
        self.youtube_api_key: str = os.environ.get("YOUTUBE_API_KEY", "")
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")
        self.database_url: str = os.environ.get("DATABASE_URL")
        if len(self.guild_ids) == 0:
            self.guild_ids = None

    def __str__(self) -> str:
        return (
            "Config: {"
            f"bot_token: {self.bot_token}, "
            f"guild_ids: {self.guild_ids}, "
            f"youtube_api_key: {self.youtube_api_key}, "
            f"log_level: {self.log_level}"
            f"database_url: {self.database_url}"
            "}"
        )
