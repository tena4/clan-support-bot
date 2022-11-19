from datetime import date, datetime, time
from http.client import HTTPException
from logging import getLogger
from typing import Callable
from zoneinfo import ZoneInfo

import app_config
import discord
import mongo_data as mongo
from discord.commands import slash_command
from discord.ext import commands, tasks
from discord.ui import InputText, Modal
from log_decorator import ButtonLogDecorator, CallbackLogDecorator, CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
btn_log = ButtonLogDecorator(logger=logger)
cmd_log = CommandLogDecorator(logger=logger)
cb_log = CallbackLogDecorator(logger=logger)

EMOJI_YET_ATK = "🍖"
EMOJI_CMP_ATK = "🦴"
EMOJI_CARRY = "🍰"


class MemoModal(Modal):
    def __init__(self, index: int, message_id: int) -> None:
        super().__init__(title="メモ入力")
        self.index = index
        self.message_id = message_id
        self.add_item(InputText(label="メモ", style=discord.InputTextStyle.singleline, required=False))

    @cb_log.log("submit a memo modal")
    async def callback(self, interaction: discord.Interaction):
        msg = await interaction.channel.fetch_message(self.message_id)
        embed = msg.embeds[0].copy()
        repo_list = embed.fields[0].value.splitlines()[1:-1]
        repo, _ = repo_list[self.index].split(" : ", maxsplit=1)
        repo_list[self.index] = f"{repo} : {interaction.user.display_name} : {self.children[0].value}"
        embed.fields[0].value = "```\n" + "\n".join(repo_list) + "\n```"
        await interaction.response.edit_message(embed=embed)


class AttarckReportView(discord.ui.View):
    def __init__(self):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.gray, label=f"凸消化{EMOJI_YET_ATK}→{EMOJI_CMP_ATK}", custom_id="attack_complete"
    )
    @btn_log.log("push attack complete button")
    async def AttackCompleteButton(self, button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        reports_field = embed.fields[0]
        repl_func: Callable[[str], str] = lambda r: r.replace(EMOJI_YET_ATK, EMOJI_CMP_ATK, 1)

        is_target, repl_reports, repo_summary = change_reports(
            reports=reports_field.value, username=interaction.user.display_name, repl_func=repl_func
        )
        if is_target is None:
            return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        reports_field.value = repl_reports
        reports_field.name = repo_summary
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        style=discord.ButtonStyle.gray, label=f"凸持越{EMOJI_YET_ATK}→{EMOJI_CARRY}", custom_id="attack_carry"
    )
    @btn_log.log("push attack carry button")
    async def AttackCarryButton(self, button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        reports_field = embed.fields[0]
        repl_func: Callable[[str], str] = lambda r: r.replace(EMOJI_YET_ATK, EMOJI_CARRY, 1)

        is_target, repl_reports, repo_summary = change_reports(
            reports=reports_field.value, username=interaction.user.display_name, repl_func=repl_func
        )
        if is_target is None:
            return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        reports_field.value = repl_reports
        reports_field.name = repo_summary
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        style=discord.ButtonStyle.gray, label=f"持越消化{EMOJI_CARRY}→{EMOJI_CMP_ATK}", custom_id="carry_complete"
    )
    @btn_log.log("push carry complete button")
    async def CarryCompleteButton(self, button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        reports_field = embed.fields[0]
        repl_func: Callable[[str], str] = lambda r: r.replace(EMOJI_CARRY, EMOJI_CMP_ATK, 1)

        is_target, repl_reports, repo_summary = change_reports(
            reports=reports_field.value, username=interaction.user.display_name, repl_func=repl_func
        )
        if is_target is None:
            return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        reports_field.value = repl_reports
        reports_field.name = repo_summary
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="全凸消化", custom_id="all_complete")
    @btn_log.log("push all complete button")
    async def AllCompleteButton(self, button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        reports_field = embed.fields[0]
        repl_func: Callable[[str], str] = lambda r: EMOJI_CMP_ATK * 3

        is_target, repl_reports, repo_summary = change_reports(
            reports=reports_field.value, username=interaction.user.display_name, repl_func=repl_func
        )
        if is_target is None:
            return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        reports_field.value = repl_reports
        reports_field.name = repo_summary
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="メモ", custom_id="report_memo", row=2)
    @btn_log.log("push report memo button")
    async def ReportMemoButton(self, button, interaction: discord.Interaction):
        reports_field = interaction.message.embeds[0].fields[0]
        repo_list = reports_field.value.splitlines()[1:-1]
        target_repo = next(
            filter(lambda a: a[1].split(" : ")[1] == interaction.user.display_name, enumerate(repo_list)), None
        )
        if target_repo is None:
            return await interaction.response.send_message("対象ユーザーではありません。")

        modal = MemoModal(index=target_repo[0], message_id=interaction.message.id)
        await interaction.response.send_modal(modal=modal)

    @discord.ui.button(style=discord.ButtonStyle.danger, label="リセット", custom_id="reset_report", row=2)
    @btn_log.log("push reset report button")
    async def ResetReportButton(self, button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        reports_field = embed.fields[0]
        repl_func: Callable[[str], str] = lambda r: EMOJI_YET_ATK * 3

        is_target, repl_reports, repo_summary = change_reports(
            reports=reports_field.value, username=interaction.user.display_name, repl_func=repl_func
        )
        if is_target is None:
            return await interaction.response.send_message("対象ユーザーではありません。", ephemeral=True)

        reports_field.value = repl_reports
        reports_field.name = repo_summary
        await interaction.response.edit_message(embed=embed)


class AttarckReportCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot
        self.scheduled_create_report.start()

    def cog_unload(self):
        self.scheduled_create_report.cancel()

    async def create_report_embed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="凸完了報告")
        clan_role = mongo.ClanMemberRole.Get(guild_id=guild.id)
        if clan_role is not None:
            all_members = await guild.fetch_members().flatten()
            member_names = [m.display_name for m in all_members if clan_role.role_id in [r.id for r in m.roles]]
            repo_list = [f"{EMOJI_YET_ATK}{EMOJI_YET_ATK}{EMOJI_YET_ATK} : {mn} : " for mn in member_names]
            embed.add_field(
                name=(
                    f"凸状況 (残凸`{EMOJI_YET_ATK}`= **{len(repo_list)}** , "
                    f"持越`{EMOJI_CARRY}`= **0** , "
                    f"消化`{EMOJI_CMP_ATK}`= **0** )"
                ),
                value="```\n" + "\n".join(repo_list) + "\n```",
            )
        return embed

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
                        navigator = AttarckReportView()
                        guild = self.bot.get_guild(reg.guild_id)
                        if guild is None:
                            guild = await self.bot.fetch_guild(reg.guild_id)
                        channel = guild.get_channel(reg.channel_id)
                        if channel is None:
                            channel = await guild.fetch_channel(reg.channel_id)
                        embed = await self.create_report_embed(guild=guild)
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
        embed = await self.create_report_embed(ctx.guild)
        await ctx.respond(embed=embed, view=navigator)

    @AttackReportCommand.error
    @cmd_log.error("attack report make command error")
    async def AttackReportCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(AttarckReportCog(bot))
    bot.persistent_view_classes.add(AttarckReportView)


def change_reports(reports: str, username: str, repl_func: Callable[[str], str]) -> tuple[bool, str, str]:
    repo_list = reports.splitlines()[1:-1]
    target_repo = next(filter(lambda a: a[1].split(" : ")[1] == username, enumerate(repo_list)), None)
    if target_repo is None:
        return False, "", ""

    repo, tails = target_repo[1].split(" : ", maxsplit=1)
    repl_repo = repl_func(repo)
    repo_list[target_repo[0]] = repl_repo + " : " + tails
    repl_reports = "```\n" + "\n".join(repo_list) + "\n```"

    yet_atk_count = sum([r.split(" : ", maxsplit=1)[0].count("🍖", 0, 3) for r in repo_list])
    yet_cmp_count = sum([r.split(" : ", maxsplit=1)[0].count("🦴", 0, 3) for r in repo_list])
    carry_count = sum([r.split(" : ", maxsplit=1)[0].count("🍰", 0, 3) for r in repo_list])
    repo_summary = (
        f"凸状況 (残凸`{EMOJI_YET_ATK}`= **{yet_atk_count}** , "
        f"持越`{EMOJI_CARRY}`= **{carry_count}** , "
        f"消化`{EMOJI_CMP_ATK}`= **{yet_cmp_count}** )"
    )

    return True, repl_reports, repo_summary
