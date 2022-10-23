import logging

import app_config
from log_formatter import CustomJsonFormatter
from mybot import BotClass

config = app_config.Config.get_instance()

log_level_map = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARN": logging.WARN, "ERROR": logging.ERROR}

logger = logging.getLogger()
logger.setLevel(log_level_map[config.log_level])
handler = logging.StreamHandler()
formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("bot start")
logger.debug(config)

bot = BotClass()

bot.load_extension("cogs.concurrent_attack_cog")
bot.load_extension("cogs.fun_cog")
bot.load_extension("cogs.tl_cog")
bot.load_extension("cogs.tl_video_cog")
bot.load_extension("cogs.db_cog")
bot.load_extension("cogs.manage_cog")
bot.load_extension("cogs.attack_report_cog")
bot.run(config.bot_token)
