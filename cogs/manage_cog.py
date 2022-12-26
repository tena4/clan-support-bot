from logging import getLogger

import discord
from discord.commands import Option, message_command, slash_command
from discord.ext import commands

import app_config
import mongo_data as mongo
from log_decorator import CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
cmd_log = CommandLogDecorator(logger=logger)


class ManageCog(commands.Cog):
    message_id_desc = "メッセージのID"
    role_desc = "ロールのID"
    status_desc = "ステータスメッセージ"

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

    @message_command(guild_ids=config.guild_ids, name="del_message")
    @cmd_log.info("call delete message msg-command")
    async def DeleteMessageMsgCommand(
        self,
        ctx: discord.ApplicationContext,
        message: discord.Message,
    ):
        if message.author.id != self.bot.application_id:
            await ctx.respond(f"対象メッセージ(ID:{message.id})はbotメッセージではありません。", ephemeral=True)
            return
        await message.delete()

        await ctx.respond(f"対象メッセージ(ID:{message.id})を削除しました。", ephemeral=True)

    @DeleteMessageMsgCommand.error
    @cmd_log.error("delete message msg-command error")
    async def DeleteMessageMsgCommand_error(self, ctx: discord.ApplicationContext, error):
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
        mongo.ClanMemberRole(guild_id=ctx.guild_id, role_id=role.id).Set()
        return await ctx.respond(f"クランメンバーのロール(ID:{role.id}, Name:{role.name})を登録しました。", ephemeral=True)

    @SetRoleCommand.error
    @cmd_log.error("set role command error")
    async def SetRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="get_role", description="登録されているクランメンバーのロールを表示する")
    @cmd_log.info("call get role command")
    async def GetRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = mongo.ClanMemberRole.Get(guild_id=ctx.guild_id)
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
        clan_role = mongo.ClanMemberRole.Get(guild_id=ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        clan_role.Delete()
        return await ctx.respond(f"クランメンバーのロール(ID:{clan_role.role_id})を登録解除しました。", ephemeral=True)

    @RemoveRoleCommand.error
    @cmd_log.error("remove role command error")
    async def RemoveRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="set_status", description="[admin]botのステータスメッセージを設定する")
    @cmd_log.info("call set status command")
    @commands.is_owner()
    async def SetStatusCommand(
        self,
        ctx: discord.ApplicationContext,
        status_msg: Option(str, status_desc, required=False, default=None),
    ):
        if status_msg:
            await self.bot.change_presence(activity=discord.Game(name=status_msg))
        else:
            await self.bot.change_presence(activity=discord.Game(name=""))
        return await ctx.respond(f"set status: {status_msg}", ephemeral=True)

    @SetStatusCommand.error
    @cmd_log.error("set status command error")
    async def SetStatusCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(ManageCog(bot))
