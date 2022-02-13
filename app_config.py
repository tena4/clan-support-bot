import os
from dotenv import load_dotenv
import json


class Config:
    def __init__(self) -> None:
        load_dotenv(verbose=True)
        self.bot_token = os.environ.get("BOT_TOKEN")
        self.guild_ids = json.loads(os.environ.get("GUILD_IDS", "[]"))
        self.boss_hps = json.loads(os.environ.get("BOSS_HPS", "[9500,10000,11000,12000,13000]"))
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        if len(self.guild_ids) == 0:
            self.guild_ids = None

    def __str__(self) -> str:
        return (
            "Config: {"
            f"bot_token: {self.bot_token}, "
            f"guild_ids: {self.guild_ids}, "
            f"boss_hps: {self.boss_hps}, "
            f"log_level: {self.log_level}"
            "}"
        )
