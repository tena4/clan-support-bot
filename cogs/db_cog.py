import calendar
from datetime import date, timedelta
from logging import getLogger

import discord
from discord.commands import Option, slash_command
from discord.ext import commands, tasks

import app_config
import mongo_data as mongo
import scraping
from log_decorator import CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
cmd_log = CommandLogDecorator(logger=logger)


class DBCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    name_desc = "ボスの名前"
    hp_desc = "ボスのHP(万)"
    start_date_desc = "開始日(yyyy-mm-dd)"
    end_date_desc = "終了日(yyyy-mm-dd)"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.scheduled_auto_setting.start()

    @slash_command(guild_ids=[config.admin_guild_id], name="set_boss", description="[admin]ボス情報の登録")
    @cmd_log.info("call set boss command")
    @commands.is_owner()
    async def SetBossCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        name: Option(str, name_desc),
        hp: Option(int, hp_desc),
    ):
        mongo.BossInfo(number=boss_num, name=name, hp=hp).Set()
        boss = mongo.BossInfo.Get(number=boss_num)
        if boss is None:
            await ctx.respond("ボス情報の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(f"ボス登録完了 番号:{boss.number}, 名前:{boss.name}, HP:{boss.hp}", ephemeral=True)

    @SetBossCommand.error
    @cmd_log.error("set boss command error")
    async def SetBossCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=[config.admin_guild_id], name="get_bosses", description="[admin]ボス情報の参照")
    @cmd_log.info("call get bosses command")
    @commands.is_owner()
    async def GetBossesCommand(self, ctx: discord.ApplicationContext):
        bosses = mongo.BossInfo.Gets()
        embed = discord.Embed(title="ボス情報一覧")
        for boss in bosses:
            embed.add_field(name=f"{boss.number}ボス", value=f"名前:{boss.name}, HP:{boss.hp}(万)", inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

    @GetBossesCommand.error
    @cmd_log.error("get bosses command error")
    async def GetBossesCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(
        guild_ids=[config.admin_guild_id], name="set_clan_battle_schedule", description="[admin]クランバトル開催期間の登録"
    )
    @cmd_log.info("call set clan battle schedule command")
    @commands.is_owner()
    async def SetClanBattleScheduleCommand(
        self,
        ctx: discord.ApplicationContext,
        start_date: Option(str, start_date_desc),
        end_date: Option(str, end_date_desc),
    ):
        mongo.ClanBattleSchedule(
            start_date=date.fromisoformat(start_date), end_date=date.fromisoformat(end_date)
        ).Set()
        schedule = mongo.ClanBattleSchedule.Get()
        if schedule is None:
            await ctx.respond("クランバトル開催期間の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(f"クランバトル開催期間登録完了 開始日:{schedule.start_date}, 終了日:{schedule.end_date}", ephemeral=True)

    @SetClanBattleScheduleCommand.error
    @cmd_log.error("call set clan battle schedule command error")
    async def SetClanBattleScheduleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(
        guild_ids=[config.admin_guild_id], name="get_clan_battle_schedule", description="[admin]クランバトル開催期間の参照"
    )
    @cmd_log.info("call get clan battle schedule command")
    @commands.is_owner()
    async def GetClanBattleScheduleCommand(self, ctx: discord.ApplicationContext):
        schedule = mongo.ClanBattleSchedule.Get()
        embed = discord.Embed(title="クランバトル開催期間")
        if schedule is not None:
            embed.add_field(name="開始日", value=schedule.start_date)
            embed.add_field(name="終了日", value=schedule.end_date)
        else:
            embed.set_footer(text="Not Found")

        await ctx.respond(embed=embed, ephemeral=True)

    @GetClanBattleScheduleCommand.error
    @cmd_log.error("get clan battle schedule command error")
    async def GetClanBattleScheduleCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=[config.admin_guild_id], name="set_auto_setting", description="[admin]自動設定切替")
    @cmd_log.info("call set auto setting command")
    @commands.is_owner()
    async def SetAutoSettingCommand(
        self,
        ctx: discord.ApplicationContext,
        schedule_enabled: Option(bool),
        boss_info_enabled: Option(bool),
    ):
        mongo.BotConfig(schedule_enabled, boss_info_enabled).Set()
        bot_config = mongo.BotConfig.Get()
        if bot_config is None:
            await ctx.respond("自動設定の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(
            f"自動設定登録完了 クランバトル開催期間:{bot_config.auto_set_clan_battle_schedule}, ボス情報:{bot_config.auto_set_boss_info}",
            ephemeral=True,
        )

    @SetAutoSettingCommand.error
    @cmd_log.error("call set auto setting command error")
    async def SetAutoSettingCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @tasks.loop(hours=6.0)
    async def scheduled_auto_setting(self):
        logger.info("run scheduled auto setting")
        bot_config = mongo.BotConfig.Get()
        if bot_config is None:
            return
        guild = self.bot.get_guild(config.admin_guild_id)
        if guild is None:
            guild = await self.bot.fetch_guild(config.admin_guild_id)
        channel = guild.get_channel(config.admin_channel_id)
        if channel is None:
            channel = await guild.fetch_channel(config.admin_channel_id)

        nowdate = date.today()
        target_lastday = calendar.monthrange(nowdate.year, nowdate.month)[1] - 1
        target_start_date = date(nowdate.year, nowdate.month, target_lastday - 4)
        target_end_date = date(nowdate.year, nowdate.month, target_lastday)

        if bot_config.auto_set_clan_battle_schedule:
            schedule = mongo.ClanBattleSchedule.Get()
            if schedule is None or schedule.start_date != target_start_date or schedule.end_date != target_end_date:
                mongo.ClanBattleSchedule(target_start_date, target_end_date).Set()
                schedule = mongo.ClanBattleSchedule.Get()
                if schedule is None:
                    await channel.send("クランバトル開催期間の自動更新に失敗しました。")
                else:
                    await channel.send(f"クランバトル開催期間を自動更新しました。開始日:{schedule.start_date}, 終了日:{schedule.end_date}")

        if (
            bot_config.auto_set_boss_info
            and target_start_date - timedelta(days=4) <= nowdate
            and target_start_date > nowdate
        ):
            boss_map = scraping.scraping(nowdate)
            if boss_map is not None:
                for b in boss_map:
                    trim_hp = b.hp // 10000
                    boss = mongo.BossInfo.Get(number=b.num)
                    if boss is None or boss.name != b.name or boss.hp != trim_hp:
                        mongo.BossInfo(number=b.num, name=b.name, hp=trim_hp).Set()
                        boss = mongo.BossInfo.Get(number=b.num)
                        if boss is None:
                            await channel.send("ボス情報の自動更新に失敗しました。")
                        else:
                            await channel.send(f"ボス情報を自動更新しました。number:{boss.number}, name:{boss.name}, hp:{boss.hp}")


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(DBCog(bot))
