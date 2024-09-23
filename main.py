import logging
import sys

from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler
from google.oauth2 import service_account

import app_config
from keep_alive import keep_alive
from log_formatter import CustomJsonFormatter, NotPyNaClFilter
from mongo_helper import MongoConn
from mybot import BotClass

config = app_config.Config.get_instance()

log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARN,
    "ERROR": logging.ERROR,
}

logger = logging.getLogger()
logger.setLevel(log_level_map[config.log_level])
handler = logging.StreamHandler()
formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

cred = service_account.Credentials.from_service_account_info(
    {
        "type": "service_account",
        "project_id": config.gcp_project_id,
        "private_key_id": config.gcp_private_key_id,
        "private_key": config.gcp_private_key.replace("\\n", "\n"),
        "client_email": config.gcp_client_mail,
        "client_id": config.gcp_client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": config.gcp_client_x509_cert_url,
    }
)
logging_client = Client(credentials=cred)
cloud_handler = CloudLoggingHandler(logging_client, name="clan-support-bot")
cloud_handler.addFilter(NotPyNaClFilter())
if logger.level < logging.INFO:
    cloud_handler.setLevel(logging.INFO)
logger.addHandler(cloud_handler)

logger.info("bot start")


def start():
    MongoConn.get_db()

    try:
        bot = BotClass()

        bot.load_extension("cogs.concurrent_attack_cog")
        bot.load_extension("cogs.fun_cog")
        bot.load_extension("cogs.tl_cog")
        bot.load_extension("cogs.db_cog")
        bot.load_extension("cogs.manage_cog")
        bot.load_extension("cogs.attack_report_cog")
        bot.load_extension("cogs.carry_over_cog")
        bot.load_extension("cogs.tl_video_cog")
        bot.run(config.bot_token)

    finally:
        logger.info("bot closing")
        MongoConn.close_conn()
        logger.info("bot closed")


keep_alive()
start()
