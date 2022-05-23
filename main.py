import logging

import app_config
import postgres_helper as pg
from mybot import BotClass

config = app_config.Config.get_instance()

log_level_map = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARN": logging.WARN, "ERROR": logging.ERROR}

logger = logging.getLogger("discord")
logger.setLevel(log_level_map[config.log_level])
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

logger.debug(config)

pg.db_init()

bot = BotClass(logger)

bot.load_extension("cogs.concurrent_attack_cog")
bot.load_extension("cogs.fun_cog")
bot.load_extension("cogs.tl_cog")
bot.load_extension("cogs.tl_video_cog")
bot.load_extension("cogs.db_cog")
bot.load_extension("cogs.manage_cog")
bot.load_extension("cogs.attack_report_cog")
bot.run(config.bot_token)
