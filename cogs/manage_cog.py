import app_config
import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from mybot import BotClass

config = app_config.Config.get_instance()


class ManageCog(commands.Cog):
    message_id_desc = "メッセージのID"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="del_message", description="botメッセージの削除")
    async def DeleteMessageCommand(
        self,
        ctx: discord.ApplicationContext,
        message_id: Option(str, message_id_desc),
    ):
        self.logger.info("call delete message command. author.id: %s", ctx.author.id)
        try:
            msg = await ctx.fetch_message(message_id)
            if msg.author.id != self.bot.application_id:
                await ctx.respond(f"対象メッセージ(ID:{message_id})はbotメッセージではありません。", ephemeral=True)
                return
            await msg.delete()

        except discord.NotFound:
            await ctx.respond(f"対象メッセージ(ID:{message_id})が見つかりませんでした。", ephemeral=True)
            return

        await ctx.respond(f"対象メッセージ(ID:{message_id})を削除しました。", ephemeral=True)

    @DeleteMessageCommand.error
    async def DeleteMessageCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("delete message command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    bot.add_cog(ManageCog(bot))
