import discord
from discord.commands import slash_command
from discord.ext import commands
from discord.commands import Option
from discord.ext.commands.context import Context
import app_config
import re
from main import BotClass
from logging import Logger
import postgres_helper as pg

config = app_config.Config()


class ConcurrentAttackButtonView(discord.ui.View):
    def __init__(self, _logger: Logger):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)
        self.logger = _logger

    # custom_id is required and should be unique for <commands.Bot.add_view>
    # attribute emoji can be used to include emojis which can be default str emoji or str(<:emojiName:int(ID)>)
    # timeout can be used if there is a timeout on the button interaction. Default timeout is set to 180.
    @discord.ui.button(style=discord.ButtonStyle.blurple, label="新凸", custom_id="new_attack")
    async def NewAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push new attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = [
            atk for atk in atk_contents if not re.match(fr"{interaction.user.display_name}\((新凸|持越)\)", atk)
        ]
        repl_atk_contents.append(f"{interaction.user.display_name}(新凸)")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.green, label="持越し凸", custom_id="carry_attack")
    async def CarryOverAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push carry over attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = [
            atk for atk in atk_contents if not re.match(fr"{interaction.user.display_name}\((新凸|持越)\)", atk)
        ]
        repl_atk_contents.append(f"{interaction.user.display_name}(持越)")
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))

    @discord.ui.button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="cancel_attack")
    async def CancelAttackButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push cancel attack button. user.id: %s", interaction.user.id)
        atk_contents = interaction.message.content.splitlines()
        repl_atk_contents = [
            atk for atk in atk_contents if not re.match(fr"{interaction.user.display_name}\((新凸|持越)\)", atk)
        ]
        await interaction.response.edit_message(content="\r\n".join(repl_atk_contents))


class ConcurrentAttackCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    hp_desc = "ボスの残りHP(万)"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="concurrent_atk", description="同時凸のテンプレートを作成する")
    async def ConcurrentAttackCommand(
        self,
        ctx: Context,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        hp: Option(int, hp_desc, required=False, default=None),
    ):
        self.bot.logger.info("call concurrent attack command. author.id: %s", ctx.author.id)
        navigator = ConcurrentAttackButtonView(self.bot.logger)
        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond(f"{boss_num}ボス情報が登録されていません。", ephemeral=True)
            return
        boss_hp = hp if hp is not None else boss.hp
        await ctx.respond(f"{boss.number}:{boss.name} 残りHP(万):{boss_hp}\r\n------", view=navigator)

    @ConcurrentAttackCommand.error
    async def ConcurrentAttackCommand_error(self, ctx: Context, error):
        self.bot.logger.error("concurrent attack command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
    bot.add_cog(ConcurrentAttackCog(bot))
