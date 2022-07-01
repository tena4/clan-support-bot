import os
import random
from logging import getLogger

import app_config
import discord
from discord.commands import slash_command
from discord.ext import commands
from log_decorator import CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
cmd_log = CommandLogDecorator(logger=logger)

ROOT_DIR = os.getcwd()


class FunCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="roll", description="サイコロを振る")
    @cmd_log.info("call roll command")
    async def RollCommand(self, ctx: discord.ApplicationContext):
        result = random.randint(1, 6)
        img_filename = f"sai{result}.png"
        sai_img_path = f"{ROOT_DIR}{os.sep}assets{os.sep}{img_filename}"
        file = discord.File(sai_img_path, filename=img_filename)
        embed = discord.Embed(title=f"dice roll : **{result}**", colour=discord.Colour.random())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=f"attachment://{img_filename}")
        await ctx.respond(embed=embed, file=file)

    @RollCommand.error
    @cmd_log.error("roll command error")
    async def RollCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="flip", description="コインを投げる")
    @cmd_log.info("call flip command")
    async def FlipCommand(self, ctx: discord.ApplicationContext):
        result = "heads" if random.randint(0, 1) == 0 else "tails"
        img_filename = f"coin_{result}.png"
        coin_img_path = f"{ROOT_DIR}{os.sep}assets{os.sep}{img_filename}"
        file = discord.File(coin_img_path, filename=img_filename)
        embed = discord.Embed(title=f"flip a coin : **{result}**", colour=discord.Colour.random())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=f"attachment://{img_filename}")
        await ctx.respond(embed=embed, file=file)

    @FlipCommand.error
    @cmd_log.error("flip command error")
    async def FlipCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(FunCog(bot))
