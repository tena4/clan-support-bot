import itertools
import math
from logging import getLogger

import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import app_config
from log_decorator import ButtonLogDecorator, CallbackLogDecorator, CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
btn_log = ButtonLogDecorator(logger=logger)
cb_log = CallbackLogDecorator(logger=logger)
cmd_log = CommandLogDecorator(logger=logger)


class CarryOverCog(commands.Cog):
    hp_desc = "ボスの残りHP(万)"
    dmg_desc = "ダメージ(万)"
    carry_time_desc = "持ち越したい時間"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="carry_over", description="同時凸時の持ち越し時間の算出")
    @cmd_log.info("call calc carry over time command")
    async def CalcCarryOverTimeCommand(
        self,
        ctx: discord.ApplicationContext,
        hp: Option(int, hp_desc, required=True),
        dmg1: Option(int, dmg_desc, required=True),
        dmg2: Option(int, dmg_desc, required=False, default=None),
        dmg3: Option(int, dmg_desc, required=False, default=None),
        dmg4: Option(int, dmg_desc, required=False, default=None),
    ):
        input_dmgs = [dmg1]
        if dmg2 is not None:
            input_dmgs.append(dmg2)
        if dmg3 is not None:
            input_dmgs.append(dmg3)
        if dmg4 is not None:
            input_dmgs.append(dmg4)

        resluts = calc_carry_over_permutations(hp, input_dmgs)
        resluts.sort(key=lambda x: x[0], reverse=True)
        results_str = ["```c"]
        for co, dmgs in resluts:
            dmgs_str = " -> ".join([str(dmg) for t, dmg in dmgs if t != "off"])

            rst_str = f"持越: {co}秒 = {dmgs_str}"
            if co >= 20:
                rst_str += "(LA)"
                through_dmgs = [str(dmg) for t, dmg in dmgs if t == "off"]
                through_dmgs.sort()
                if through_dmgs:
                    through_dmgs_str = ", ".join(through_dmgs)
                    rst_str += f" --- 流し: {through_dmgs_str}"
            else:
                rst_str += "(未討伐)"
            if rst_str not in results_str:
                results_str.append(rst_str)
        results_str.append("```")
        embed = discord.Embed(title="持ち越し時間算出")
        embed.add_field(name=f"{self.hp_desc}:{hp}", value="\n".join(results_str))
        await ctx.respond(embed=embed)

    @CalcCarryOverTimeCommand.error
    @cmd_log.error("calc carry over time command error")
    async def CalcCarryOverTimeCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="fullback", description="持ち越したい時間に必要なダメージの算出")
    @cmd_log.info("call calc fullback damage command")
    async def CalcFullbackDamageCommand(
        self,
        ctx: discord.ApplicationContext,
        hp: Option(int, hp_desc, required=True),
        carry_time: Option(int, carry_time_desc, required=False, default=90),
    ):
        dmg = math.ceil(hp * 90 / (90 - carry_time + 21))

        results_str = ["```c"]
        results_str.append(f"持越: {carry_time}秒 = {dmg}")
        results_str.append("```")
        embed = discord.Embed(title="必要ダメージ算出")
        embed.add_field(name=f"{self.hp_desc}:{hp}", value="\n".join(results_str))
        await ctx.respond(embed=embed)

    @CalcFullbackDamageCommand.error
    @cmd_log.error("calc fullback damage command error")
    async def CalcFullbackDamageCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(CarryOverCog(bot))


def calc_carry_over_permutations(hp: int, input_dmgs: list[int]) -> list[tuple]:
    resluts = []
    for choice_dmgs in itertools.permutations(input_dmgs):
        calc_hp = hp
        calc_dmgs = []
        carry_over = 0
        for dmg in choice_dmgs:
            if calc_hp - dmg > 0:
                calc_hp -= dmg
                calc_dmgs.append(("th", dmg))
            elif calc_hp > 0:
                calc_hp -= dmg
                carry_over = math.ceil(((-calc_hp) / dmg) * 90 + 20)
                if carry_over > 90:
                    carry_over = 90
                calc_dmgs.sort(key=lambda d: d[1], reverse=True)
                calc_dmgs.append(("la", dmg))
            else:
                calc_dmgs.append(("off", dmg))
        resluts.append((carry_over, calc_dmgs))

    return resluts
