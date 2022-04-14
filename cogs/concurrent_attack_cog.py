import discord
from discord.commands import slash_command
from discord.ext import commands
from discord.commands import Option
import app_config
import re
from logging import Logger
from typing import Optional
import postgres_helper as pg
from mybot import BotClass

config = app_config.Config.get_instance()


class ConcurrentAttackButtonView(discord.ui.View):
    def __init__(self, _logger: Logger):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)
        self.logger = _logger

    # custom_id is required and should be unique for <commands.Bot.add_view>
    # attribute emoji can be used to include emojis which can be default str emoji or str(<:emojiName:int(ID)>)
    # timeout can be used if there is a timeout on the button interaction. Default timeout is set to 180.
    @discord.ui.button(style=discord.ButtonStyle.blurple, label="新凸:物\N{Boxing Glove}", custom_id="new_physics_attack")
    async def NewPhysicsAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push new physics attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = replace_attacks(atk_contents, interaction.user.display_name, "　新凸　 物\N{Boxing Glove}")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="新凸:魔\N{Mage}", custom_id="new_magic_attack")
    async def NewMagicAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push new magic attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = replace_attacks(atk_contents, interaction.user.display_name, "　新凸　 魔\N{Mage}")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.green, label="持越:物\N{Boxing Glove}", custom_id="carry_physics_attack")
    async def CarryOverPhysicsAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push carry over physics attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = replace_attacks(atk_contents, interaction.user.display_name, "★持越★ 物\N{Boxing Glove}")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.green, label="持越:魔\N{Mage}", custom_id="carry_magic_attack")
    async def CarryOverMagicAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push carry over magic attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = replace_attacks(atk_contents, interaction.user.display_name, "★持越★ 魔\N{Mage}")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="cancel_attack")
    async def CancelAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push cancel attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = replace_attacks(atk_contents, interaction.user.display_name, None)
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))


class ConcurrentAttackCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    hp_desc = "ボスの残りHP(万)"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="concurrent_atk", description="同時凸のテンプレートを作成する")
    async def ConcurrentAttackCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        hp: Option(int, hp_desc, required=False, default=None),
    ):
        self.logger.info("call concurrent attack command. author.id: %s", ctx.author.id)
        navigator = ConcurrentAttackButtonView(self.logger)
        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond(f"{boss_num}ボス情報が登録されていません。", ephemeral=True)
            return
        boss_hp = hp if hp is not None else boss.hp
        await ctx.respond(f"{boss.number}:{boss.name} 残りHP(万):{boss_hp}\r\n------", view=navigator)

    @ConcurrentAttackCommand.error
    async def ConcurrentAttackCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("concurrent attack command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
    bot.add_cog(ConcurrentAttackCog(bot))


def replace_attacks(atk_list: list[str], username: str, repl_atk: Optional[str]) -> list[str]:
    repl_atk_list = [atk for atk in atk_list if not re.match(fr".*\s{username}$", atk)]
    if repl_atk is not None:
        repl_atk_list.append(f"{repl_atk}  {username}")
    return repl_atk_list
