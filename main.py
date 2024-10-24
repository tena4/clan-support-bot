import logging

import sentry_sdk

import app_config
from keep_alive import keep_alive
from log_formatter import CustomJsonFormatter
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
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


sentry_sdk.init(
    dsn=config.sentry_dsn,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

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
