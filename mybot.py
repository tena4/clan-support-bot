from logging import getLogger

import discord

import app_config

logger = getLogger(__name__)
config = app_config.Config.get_instance()


class BotClass(discord.Bot):
    def __init__(self):
        super().__init__()
        self.persistent_views_added = False
        self.persistent_view_classes = set()

    # For making the intreaction Button works even after restart.
    async def on_ready(self):
        if not self.persistent_views_added:

            # You can add <discord.ui.View> classes to the <commands.Bot.add_view> to make it work after restart
            # self.add_view(<discord.ui.View>)
            for vs in self.persistent_view_classes:
                self.add_view(vs())

            logger.info(f"Connected as {self.user}", extra={"user_id": self.user.id})
            self.persistent_views_added = True
            logger.info("Bot initialization completed")
