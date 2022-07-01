from logging import getLogger

import app_config
import discord
import postgres_helper as pg
from discord.commands import Option, slash_command
from discord.ext import commands
from log_decorator import CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
cmd_log = CommandLogDecorator(logger=logger)


class ManageCog(commands.Cog):
    message_id_desc = "メッセージのID"
    role_desc = "ロールのID"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="del_message", description="botメッセージの削除")
    @cmd_log.info("call delete message command")
    async def DeleteMessageCommand(
        self,
        ctx: discord.ApplicationContext,
        message_id: Option(str, message_id_desc),
    ):
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
    @cmd_log.error("delete message command error")
    async def DeleteMessageCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="set_role", description="クランメンバーのロールを登録する")
    @cmd_log.info("call set role command")
    async def SetRoleCommand(
        self,
        ctx: discord.ApplicationContext,
        role_id: Option(str, role_desc),
    ):
        role = ctx.guild.get_role(int(role_id))
        if role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)
        pg.set_clan_member_role(ctx.guild_id, role.id)
        return await ctx.respond(f"クランメンバーのロール(ID:{role.id}, Name:{role.name})を登録しました。", ephemeral=True)

    @SetRoleCommand.error
    @cmd_log.error("set role command error")
    async def SetRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="get_role", description="クランメンバーのロールを登録する")
    @cmd_log.info("call get role command")
    async def GetRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = pg.get_clan_member_role(ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        role = ctx.guild.get_role(clan_role.role_id)
        return await ctx.respond(f"クランメンバーのロール(ID:{role.id}, Name:{role.name})が登録されています。", ephemeral=True)

    @GetRoleCommand.error
    @cmd_log.error("get role command error")
    async def GetRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="remove_role", description="クランメンバーのロールを登録解除する")
    @cmd_log.info("call remove role command")
    async def RemoveRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = pg.get_clan_member_role(ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        pg.remove_clan_member_role(ctx.guild_id)
        return await ctx.respond(f"クランメンバーのロール(ID:{clan_role.role_id})を登録解除しました。", ephemeral=True)

    @RemoveRoleCommand.error
    @cmd_log.error("remove role command error")
    async def RemoveRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(ManageCog(bot))
