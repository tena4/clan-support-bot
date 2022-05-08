import os
import random

import app_config
import discord
from discord.commands import slash_command
from discord.ext import commands
from mybot import BotClass

ROOT_DIR = os.getcwd()
config = app_config.Config.get_instance()


class FunCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="roll", description="サイコロを振る")
    async def RollCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call roll command. author.id: %s", ctx.author.id)
        result = random.randint(1, 6)
        img_filename = f"sai{result}.png"
        sai_img_path = f"{ROOT_DIR}{os.sep}assets{os.sep}{img_filename}"
        file = discord.File(sai_img_path, filename=img_filename)
        embed = discord.Embed(title=f"dice roll : **{result}**", colour=discord.Colour.random())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=f"attachment://{img_filename}")
        await ctx.respond(embed=embed, file=file)

    @RollCommand.error
    async def RollCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("roll command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="flip", description="コインを投げる")
    async def FlipCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call flip command. author.id: %s", ctx.author.id)
        result = "heads" if random.randint(0, 1) == 0 else "tails"
        img_filename = f"coin_{result}.png"
        coin_img_path = f"{ROOT_DIR}{os.sep}assets{os.sep}{img_filename}"
        file = discord.File(coin_img_path, filename=img_filename)
        embed = discord.Embed(title=f"flip a coin : **{result}**", colour=discord.Colour.random())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=f"attachment://{img_filename}")
        await ctx.respond(embed=embed, file=file)

    @FlipCommand.error
    async def FlipCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("flip command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    bot.add_cog(FunCog(bot))
