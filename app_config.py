import json
import os
from typing import Optional

from dotenv import load_dotenv


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
        self.admin_guild_id: str = os.environ.get("ADMIN_GUILD_ID")
        self.admin_channel_id: str = os.environ.get("ADMIN_CHANNEL_ID")
        self.guild_ids: Optional[list[str]] = json.loads(os.environ.get("GUILD_IDS", "[]"))
        self.youtube_api_keys: list[str] = json.loads(os.environ.get("YOUTUBE_API_KEYS", "[]"))
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")
        self.database_url: str = os.environ.get("DATABASE_URL")
        self.gcp_project_id: str = os.environ["GCP_PROJECT_ID"]
        self.gcp_private_key_id: str = os.environ["GCP_PRIVATE_KEY_ID"]
        self.gcp_private_key: str = os.environ["GCP_PRIVATE_KEY"]
        self.gcp_client_mail: str = os.environ["GCP_CLIENT_MAIL"]
        self.gcp_client_id: str = os.environ["GCP_CLIENT_ID"]
        self.gcp_client_x509_cert_url: str = os.environ["GCP_CLIENT_X509_CERT_URL"]
        self.scraping_template_url: str = os.environ["SCRAPING_TEMPLATE_URL"]
        if len(self.guild_ids) == 0:
            self.guild_ids = None
