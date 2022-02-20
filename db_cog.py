import discord
from discord.commands import slash_command, Option
from discord.ext import commands
from discord.ext.commands.context import Context
import app_config
from main import BotClass
import postgres_helper as pg

config = app_config.Config()


class DBCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    name_desc = "ボスの名前"
    hp_desc = "ボスのHP(万)"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="set_boss", description="ボス情報の登録")
    @commands.is_owner()
    async def SetBossCommand(
        self,
        ctx: Context,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        name: Option(str, name_desc),
        hp: Option(int, hp_desc),
    ):
        self.bot.logger.info("call set boss command. author.id: %s", ctx.author.id)
        pg.set_boss_info(boss_num, name, hp)
        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond("ボス情報の登録に失敗しました。", ephemeral=True)
            return

        await ctx.respond(f"ボス登録完了 番号:{boss.number}, 名前:{boss.name}, HP:{boss.hp}", ephemeral=True)

    @SetBossCommand.error
    async def SetBossCommand_error(self, ctx: Context, error):
        self.bot.logger.error("set boss command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="get_bosses", description="ボス情報の参照")
    @commands.is_owner()
    async def GetBossesCommand(self, ctx: Context):
        self.bot.logger.info("call get bosses command. author.id: %s", ctx.author.id)
        bosses = pg.get_bosses_info()
        embed = discord.Embed(title="ボス情報一覧")
        for boss in bosses:
            embed.add_field(name=f"{boss.number}ボス", value=f"名前:{boss.name}, HP:{boss.hp}(万)", inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

    @GetBossesCommand.error
    async def GetBossesCommand_error(self, ctx: Context, error):
        self.bot.logger.error("get bosses command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
    bot.add_cog(DBCog(bot))
