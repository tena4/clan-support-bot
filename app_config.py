import os
from typing import Optional
from dotenv import load_dotenv
import json


class Singleton(object):
    @classmethod
    def get_instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


class Config(Singleton):
    def __init__(self) -> None:
        load_dotenv(verbose=True)
        self.bot_token: str = os.environ.get("BOT_TOKEN")
        self.guild_ids: Optional[list[str]] = json.loads(os.environ.get("GUILD_IDS", "[]"))
        self.youtube_api_keys: list[str] = json.loads(os.environ.get("YOUTUBE_API_KEYS", "[]"))
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")
        self.database_url: str = os.environ.get("DATABASE_URL")
        if len(self.guild_ids) == 0:
            self.guild_ids = None

    def __str__(self) -> str:
        return (
            "Config: {"
            f"bot_token: {self.bot_token}, "
            f"guild_ids: {self.guild_ids}, "
            f"youtube_api_keys: {self.youtube_api_keys}, "
            f"log_level: {self.log_level}"
            f"database_url: {self.database_url}"
            "}"
        )
