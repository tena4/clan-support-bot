from datetime import date
import discord
from discord.commands import slash_command, Option
from discord.ext import commands
import app_config
import postgres_helper as pg
from mybot import BotClass

config = app_config.Config.get_instance()


class DBCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    name_desc = "ボスの名前"
    hp_desc = "ボスのHP(万)"
    start_date_desc = "開始日(yyyy-mm-dd)"
    end_date_desc = "終了日(yyyy-mm-dd)"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="set_boss", description="[admin]ボス情報の登録")
    @commands.is_owner()
    async def SetBossCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        name: Option(str, name_desc),
        hp: Option(int, hp_desc),
    ):
        self.logger.info("call set boss command. author.id: %s", ctx.author.id)
        pg.set_boss_info(boss_num, name, hp)
        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond("ボス情報の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(f"ボス登録完了 番号:{boss.number}, 名前:{boss.name}, HP:{boss.hp}", ephemeral=True)

    @SetBossCommand.error
    async def SetBossCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("set boss command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="get_bosses", description="[admin]ボス情報の参照")
    @commands.is_owner()
    async def GetBossesCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call get bosses command. author.id: %s", ctx.author.id)
        bosses = pg.get_bosses_info()
        embed = discord.Embed(title="ボス情報一覧")
        for boss in bosses:
            embed.add_field(name=f"{boss.number}ボス", value=f"名前:{boss.name}, HP:{boss.hp}(万)", inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

    @GetBossesCommand.error
    async def GetBossesCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("get bosses command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="set_clan_battle_schedule", description="[admin]クランバトル開催期間の登録")
    @commands.is_owner()
    async def SetClanBattleScheduleCommand(
        self,
        ctx: discord.ApplicationContext,
        start_date: Option(str, start_date_desc),
        end_date: Option(str, end_date_desc),
    ):
        self.logger.info("call set clan battle schedule command. author.id: %s", ctx.author.id)
        pg.set_clan_battle_schedule(start_date=date.fromisoformat(start_date), end_date=date.fromisoformat(end_date))
        schedule = pg.get_clan_battle_schedule()
        if schedule is None:
            await ctx.respond("クランバトル開催期間の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(f"クランバトル開催期間登録完了 開始日:{schedule.start_date}, 終了日:{schedule.end_date}", ephemeral=True)

    @SetClanBattleScheduleCommand.error
    async def SetClanBattleScheduleCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("set clan battle schedule command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="get_clan_battle_schedule", description="[admin]クランバトル開催期間の参照")
    @commands.is_owner()
    async def GetClanBattleScheduleCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call get clan battle schedule command. author.id: %s", ctx.author.id)
        schedule = pg.get_clan_battle_schedule()
        embed = discord.Embed(title="クランバトル開催期間")
        if schedule is not None:
            embed.add_field(name="開始日", value=schedule.start_date)
            embed.add_field(name="終了日", value=schedule.end_date)
        else:
            embed.set_footer(text="Not Found")

        await ctx.respond(embed=embed, ephemeral=True)

    @GetClanBattleScheduleCommand.error
    async def GetClanBattleScheduleCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("get clan battle schedule command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
    bot.add_cog(DBCog(bot))
