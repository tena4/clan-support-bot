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
    role_desc = "ロール"
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

    @slash_command(guild_ids=config.guild_ids, name="set_clan_member_role", description="クランメンバーのロールを登録する")
    @cmd_log.info("call clan member set role command")
    async def SetClanMemberRoleCommand(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, role_desc),
    ):
        mongo.ClanMemberRole(guild_id=ctx.guild_id, role_id=role.id).Set()
        return await ctx.respond(f"クランメンバーのロール(ID:{role.id}, Name:{role.name})を登録しました。", ephemeral=True)

    @SetClanMemberRoleCommand.error
    @cmd_log.error("set clan member role command error")
    async def SetClanMemberRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="get_clan_member_role", description="登録されているクランメンバーのロールを表示する")
    @cmd_log.info("call get clan member role command")
    async def GetClanMemberRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = mongo.ClanMemberRole.Get(guild_id=ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        role = ctx.guild.get_role(clan_role.role_id)
        return await ctx.respond(f"クランメンバーのロール(ID:{role.id}, Name:{role.name})が登録されています。", ephemeral=True)

    @GetClanMemberRoleCommand.error
    @cmd_log.error("get clan member role command error")
    async def GetClanMemberRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="remove_clan_member_role", description="クランメンバーのロールを登録解除する")
    @cmd_log.info("call remove clan member role command")
    async def RemoveClanMemberRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = mongo.ClanMemberRole.Get(guild_id=ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        clan_role.Delete()
        return await ctx.respond(f"クランメンバーのロール(ID:{clan_role.role_id})を登録解除しました。", ephemeral=True)

    @RemoveClanMemberRoleCommand.error
    @cmd_log.error("remove clan member role command error")
    async def RemoveClanMemberRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="set_yet_complete_role", description="未完了凸のロールを登録する")
    @cmd_log.info("call set yet complete role command")
    async def SetYetCompleteRoleCommand(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, role_desc),
    ):
        mongo.YetCompleteRole(guild_id=ctx.guild_id, role_id=role.id).Set()
        return await ctx.respond(f"未完了凸のロール(ID:{role.id}, Name:{role.name})を登録しました。", ephemeral=True)

    @SetYetCompleteRoleCommand.error
    @cmd_log.error("set yet complete role command error")
    async def SetYetCompleteRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="get_yet_complete_role", description="登録されている未完了凸のロールを表示する")
    @cmd_log.info("call get yet complete role command")
    async def GetYetCompleteRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = mongo.YetCompleteRole.Get(guild_id=ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        role = ctx.guild.get_role(clan_role.role_id)
        return await ctx.respond(f"未完了凸のロール(ID:{role.id}, Name:{role.name})が登録されています。", ephemeral=True)

    @GetYetCompleteRoleCommand.error
    @cmd_log.error("get yet complete role command error")
    async def GetYetCompleteRoleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)

    @slash_command(guild_ids=config.guild_ids, name="remove_yet_complete_role", description="未完了凸のロールを登録解除する")
    @cmd_log.info("call yet complete remove role command")
    async def RemoveYetCompleteRoleCommand(
        self,
        ctx: discord.ApplicationContext,
    ):
        clan_role = mongo.YetCompleteRole.Get(guild_id=ctx.guild_id)
        if clan_role is None:
            return await ctx.respond("該当するロールが存在しません。", ephemeral=True)

        clan_role.Delete()
        return await ctx.respond(f"未完了凸のロール(ID:{clan_role.role_id})を登録解除しました。", ephemeral=True)

    @RemoveYetCompleteRoleCommand.error
    @cmd_log.error("remove yet complete role command error")
    async def RemoveYetCompleteRoleCommand_error(self, ctx: discord.ApplicationContext, error):
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
