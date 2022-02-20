import discord
import app_config
import logging


config = app_config.Config()


class BotClass(discord.Bot):
    def __init__(self, _logger: logging.Logger):
        super().__init__()
        self.persistent_views_added = False
        self.logger = _logger

    # For making the intreaction Button works even after restart.
    async def on_ready(self):
        if not self.persistent_views_added:

            # You can add <discord.ui.View> classes to the <commands.Bot.add_view> to make it work after restart
            # self.add_view(<discord.ui.View>)

            self.logger.info(f"Connected as {self.user} with ID {self.user.id}")
            self.logger.info("------")
            self.persistent_views_added = True


if __name__ == "__main__":
    log_lv_map = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARN": logging.WARN, "ERROR": logging.ERROR}

    logger = logging.getLogger("discord")
    logger.setLevel(log_lv_map[config.log_level])
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)

    logger.debug(config)

    bot = BotClass(logger)

    bot.load_extension("concurrent_attack_cog")
    bot.load_extension("fun_cog")
    bot.load_extension("tl_cog")
    bot.load_extension("tl_video_cog")
    bot.load_extension("db_cog")
    bot.run(config.bot_token)
