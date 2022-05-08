from datetime import date, datetime, time
from http.client import HTTPException
from logging import Logger
from zoneinfo import ZoneInfo

import app_config
import discord
import postgres_helper as pg
from discord.commands import slash_command
from discord.ext import commands, tasks
from mybot import BotClass

config = app_config.Config.get_instance()


class AttarckReportView(discord.ui.View):
    def __init__(self, _logger: Logger):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)
        self.logger = _logger

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="3凸完了", custom_id="attack_finished")
    async def AttackFinishedButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push attack finished button. user.id: %s", interaction.user.id)
        report_field = next(filter(lambda f: f.name == "3凸完了", interaction.message.embeds[0].fields), None)
        if report_field is None:
            return await interaction.response.send_message("error", ephemeral=True)
        reporters = report_field.value.splitlines()
        if interaction.user.display_name not in reporters:
            reporters.append(interaction.user.display_name)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="\n".join(reporters))
        embed.add_field(name="凸完人数", value=str(len(reporters) - 1))
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="attack_finished_cancel")
    async def AttackFinishedCancelButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push attack finished cancel button. user.id: %s", interaction.user.id)
        report_field = next(filter(lambda f: f.name == "3凸完了", interaction.message.embeds[0].fields), None)
        if report_field is None:
            return await interaction.response.send_message("error", ephemeral=True)
        reporters = report_field.value.splitlines()
        if interaction.user.display_name in reporters:
            reporters.remove(interaction.user.display_name)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="\n".join(reporters))
        embed.add_field(name="凸完人数", value=str(len(reporters) - 1))
        await interaction.response.edit_message(embed=embed)


class AttarckReportCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger
        self.scheduled_create_report.start()

    def cog_unload(self):
        self.scheduled_create_report.cancel()

    @tasks.loop(time=time(hour=20, minute=0))
    async def scheduled_create_report(self):
        self.logger.info("run scheduled create report")
        now_date = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        cbs = pg.get_clan_battle_schedule()
        if cbs is None:
            return
        elif now_date >= cbs.start_date and now_date <= cbs.end_date:
            day_index = (now_date - cbs.start_date).days
            reglist = pg.get_attack_report_register_list()
            err_channels = []
            for reg in reglist:
                if reg.last_published < now_date:
                    try:
                        guild = self.bot.get_guild(reg.guild_id)
                        if guild is None:
                            guild = await self.bot.fetch_guild(reg.guild_id)
                        channel = guild.get_channel(reg.channel_id)
                        if channel is None:
                            channel = await guild.fetch_channel(reg.channel_id)
                        navigator = AttarckReportView(self.logger)
                        embed = discord.Embed(title="凸完了報告")
                        embed.add_field(name="3凸完了", value="-----")
                        embed.add_field(name="凸完人数", value="0")
                        await channel.send(content=f"{day_index + 1}日目", embed=embed, view=navigator)

                    except discord.NotFound:
                        # 編集するメッセージがない(削除された)場合、subsc_msgsから当メッセージを外す
                        self.logger.info("remove attack report register. channel.id: %s", reg.channel_id)
                        err_channels.append(reg)
                    except HTTPException as e:
                        self.logger.error("error create attack report. channel.id: %s. error: %s", reg.channel_id, e)
                    else:
                        pg.set_attack_report_register(reg.guild_id, reg.channel_id, now_date)

            for err_ch in err_channels:
                pg.remove_attack_report_register(err_ch.guild_id, cbs.channel_id)

    @slash_command(guild_ids=config.guild_ids, name="atk_report_auto_register", description="凸完了報告表の自動作成を登録する")
    async def AttackReportAutoRegisterCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call attack report make auto register command. author.id: %s", ctx.author.id)
        reglist = pg.get_attack_report_register_list()
        reg = next(filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, reglist), None)
        if reg is None:
            pg.set_attack_report_register(ctx.guild.id, ctx.channel.id, date(2020, 1, 1))
            await ctx.respond("このチャンネルに凸完了報告表の自動作成を登録しました")
        else:
            await ctx.respond("このチャンネルに凸完了報告表の自動作成は既に登録されています", ephemeral=True)

    @AttackReportAutoRegisterCommand.error
    async def AttackReportAutoRegisterCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("attack report make auto register command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="atk_report_auto_unregister", description="凸完了報告表の自動作成の登録を解除する")
    async def AttackReportAutoUnregisterCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call attack report make auto unregister command. author.id: %s", ctx.author.id)
        reglist = pg.get_attack_report_register_list()
        reg = next(filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, reglist), None)
        if reg is not None:
            pg.remove_attack_report_register(ctx.guild.id, ctx.channel.id)
            await ctx.respond("このチャンネルに登録されていた凸完了報告表の自動作成を解除しました")
        else:
            await ctx.respond("このチャンネルに凸完了報告表の自動作成は登録されていません", ephemeral=True)

    @AttackReportAutoUnregisterCommand.error
    async def AttackReportAutoUnregisterCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("attack report make auto unregister command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="atk_report_make", description="凸完了報告表を作成")
    async def AttackReportCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call attack report make command. author.id: %s", ctx.author.id)
        navigator = AttarckReportView(self.logger)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="-----")
        embed.add_field(name="凸完人数", value="0")
        await ctx.respond(embed=embed, view=navigator)

    @AttackReportCommand.error
    async def AttackReportCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("attack report make command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    bot.add_cog(AttarckReportCog(bot))
    bot.persistent_view_classes.add(AttarckReportView)
