import discord
from discord.commands import slash_command
from discord.ext import commands
from discord.ext.commands.context import Context
import app_config
from logging import Logger

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
    def __init__(self, bot):
        self.bot = bot
        self.logger: Logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="report_make", description="凸完了報告メッセージを作成")
    async def AttackReportCommand(self, ctx: Context):
        self.logger.info("call attack report make command. author.id: %s", ctx.author.id)
        navigator = AttarckReportView(self.logger)
        embed = discord.Embed(title="凸完了報告")
        embed.add_field(name="3凸完了", value="-----")
        embed.add_field(name="凸完人数", value="0")
        await ctx.respond(embed=embed, view=navigator)

    @AttackReportCommand.error
    async def AttackReportCommand_error(self, ctx: Context, error):
        self.logger.error("attack report make command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
    bot.add_cog(AttarckReportCog(bot))
