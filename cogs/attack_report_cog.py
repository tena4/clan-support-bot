from datetime import date, datetime, time
from http.client import HTTPException
from logging import getLogger
from zoneinfo import ZoneInfo

import app_config
import discord
import mongo_data as mongo
from discord.commands import slash_command
from discord.ext import commands, tasks
from log_decorator import ButtonLogDecorator, CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
btn_log = ButtonLogDecorator(logger=logger)
cmd_log = CommandLogDecorator(logger=logger)


class AttarckReportView(discord.ui.View):
    def __init__(self):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="3凸完了", custom_id="attack_finished")
    @btn_log.log("push attack finished button")
    async def AttackFinishedButton(self, button, interaction: discord.Interaction):
        report_field = next(filter(lambda f: f.name == "3凸完了", interaction.message.embeds[0].fields), None)
        if report_field is None:
            return await interaction.response.send_message("error", ephemeral=True)
        yet_report_field = next(filter(lambda f: f.name == "3凸未完", interaction.message.embeds[0].fields), None)
        reporters = report_field.value.splitlines()
        if yet_report_field is not None:
            yet_reporters = yet_report_field.value.splitlines()
            if interaction.user.display_name not in (reporters + yet_reporters):
                return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        if interaction.user.display_name not in reporters:
            reporters.append(interaction.user.display_name)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="\n".join(reporters))
        if yet_report_field is not None:
            if interaction.user.display_name in yet_reporters:
                yet_reporters.remove(interaction.user.display_name)
            embed.add_field(name="3凸未完", value="\n".join(yet_reporters))
        embed.add_field(name="凸完人数", value=str(len(reporters) - 1))
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="attack_finished_cancel")
    @btn_log.log("push attack finished cancel button")
    async def AttackFinishedCancelButton(self, button, interaction: discord.Interaction):
        report_field = next(filter(lambda f: f.name == "3凸完了", interaction.message.embeds[0].fields), None)
        if report_field is None:
            return await interaction.response.send_message("error", ephemeral=True)
        yet_report_field = next(filter(lambda f: f.name == "3凸未完", interaction.message.embeds[0].fields), None)
        reporters = report_field.value.splitlines()
        if yet_report_field is not None:
            yet_reporters = yet_report_field.value.splitlines()
            if interaction.user.display_name not in (reporters + yet_reporters):
                return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        if interaction.user.display_name in reporters:
            reporters.remove(interaction.user.display_name)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="\n".join(reporters))
        if yet_report_field is not None:
            if interaction.user.display_name not in yet_reporters:
                yet_reporters.append(interaction.user.display_name)
            embed.add_field(name="3凸未完", value="\n".join(yet_reporters))
        embed.add_field(name="凸完人数", value=str(len(reporters) - 1))
        await interaction.response.edit_message(embed=embed)


class AttarckReportCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot
        self.scheduled_create_report.start()

    def cog_unload(self):
        self.scheduled_create_report.cancel()

    @tasks.loop(time=time(hour=20, minute=0))
    async def scheduled_create_report(self):
        logger.info("run scheduled create report")
        now_date = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        cbs = mongo.ClanBattleSchedule.Get()
        if cbs is None:
            return
        elif now_date >= cbs.start_date and now_date <= cbs.end_date:
            day_index = (now_date - cbs.start_date).days
            reglist = mongo.AttackReportRegister.Gets()
            err_reglist: list[mongo.AttackReportRegister] = []
            for reg in reglist:
                if reg.last_published < now_date:
                    try:
                        guild = self.bot.get_guild(reg.guild_id)
                        if guild is None:
                            guild = await self.bot.fetch_guild(reg.guild_id)
                        channel = guild.get_channel(reg.channel_id)
                        if channel is None:
                            channel = await guild.fetch_channel(reg.channel_id)
                        navigator = AttarckReportView()
                        embed = discord.Embed(title="凸完了報告")
                        embed.add_field(name="3凸完了", value="-----")
                        clan_role = mongo.ClanMemberRole.Get(guild_id=reg.guild_id)
                        if clan_role is not None:
                            all_members = await guild.fetch_members().flatten()
                            member_names = [
                                m.display_name for m in all_members if clan_role.role_id in [r.id for r in m.roles]
                            ]
                            embed.add_field(name="3凸未完", value="\n".join(["-----"] + member_names))
                        embed.add_field(name="凸完人数", value="0")
                        await channel.send(content=f"{day_index + 1}日目", embed=embed, view=navigator)

                    except discord.NotFound:
                        err_reglist.append(reg)
                    except HTTPException:
                        logger.error(
                            "HTTP exception by create attack report",
                            exc_info=True,
                            extra={
                                "channel_id": reg.channel_id,
                            },
                        )
                    except Exception:
                        logger.error(
                            "unknown exception by create attack report",
                            exc_info=True,
                            extra={
                                "channel_id": reg.channel_id,
                            },
                        )
                    else:
                        reg.last_published = now_date
                        reg.Set()

            for err_reg in err_reglist:
                # 対象チャンネルがない(削除された)場合、report_registerから当チャンネルを外す
                logger.info(
                    "remove attack report register",
                    extra={
                        "channel_id": err_reg.channel_id,
                    },
                )
                err_reg.Delete()

    @slash_command(guild_ids=config.guild_ids, name="atk_report_auto_register", description="凸完了報告表の自動作成を登録する")
    @cmd_log.info("call attack report make auto register command")
    async def AttackReportAutoRegisterCommand(self, ctx: discord.ApplicationContext):
        reglist = mongo.AttackReportRegister.Gets()
        reg = next(filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, reglist), None)
        if reg is None:
            mongo.AttackReportRegister(ctx.guild.id, ctx.channel.id, date(2020, 1, 1)).Set()
            await ctx.respond("このチャンネルに凸完了報告表の自動作成を登録しました")
        else:
            await ctx.respond("このチャンネルに凸完了報告表の自動作成は既に登録されています", ephemeral=True)

    @AttackReportAutoRegisterCommand.error
    @cmd_log.error("attack report make auto register command error")
    async def AttackReportAutoRegisterCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="atk_report_auto_unregister", description="凸完了報告表の自動作成の登録を解除する")
    @cmd_log.info("call attack report make auto unregister command")
    async def AttackReportAutoUnregisterCommand(self, ctx: discord.ApplicationContext):
        reglist = mongo.AttackReportRegister.Gets()
        reg = next(filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, reglist), None)
        if reg is not None:
            reg.Delete()
            await ctx.respond("このチャンネルに登録されていた凸完了報告表の自動作成を解除しました")
        else:
            await ctx.respond("このチャンネルに凸完了報告表の自動作成は登録されていません", ephemeral=True)

    @AttackReportAutoUnregisterCommand.error
    @cmd_log.error("attack report make auto unregister command error")
    async def AttackReportAutoUnregisterCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="atk_report_make", description="凸完了報告表を作成")
    @cmd_log.info("call attack report make command")
    async def AttackReportCommand(self, ctx: discord.ApplicationContext):
        navigator = AttarckReportView()
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="-----")
        clan_role = mongo.ClanMemberRole.Get(guild_id=ctx.guild_id)
        if clan_role is not None:
            all_members = await ctx.guild.fetch_members().flatten()
            member_names = [m.display_name for m in all_members if clan_role.role_id in [r.id for r in m.roles]]
            embed.add_field(name="3凸未完", value="\n".join(["-----"] + member_names))
        embed.add_field(name="凸完人数", value="0")
        await ctx.respond(embed=embed, view=navigator)

    @AttackReportCommand.error
    @cmd_log.error("attack report make command error")
    async def AttackReportCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(AttarckReportCog(bot))
    bot.persistent_view_classes.add(AttarckReportView)
