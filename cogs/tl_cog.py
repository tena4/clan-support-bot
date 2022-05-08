import re
from logging import Logger

import app_config
import char
import discord
from discord.commands import slash_command
from discord.ext import commands
from discord.ui import InputText, Modal
from mybot import BotClass

config = app_config.Config.get_instance()
BASE_SECONDS = 90


class TLConvertModal(Modal):
    def __init__(self) -> None:
        super().__init__(title="TL秒数変換")

        self.add_item(
            InputText(
                label="TL (※対応時刻フォーマット=[mm:ss, m:ss])",
                placeholder="TL本文を貼り付けて下さい",
                style=discord.InputTextStyle.long,
                max_length=4000,
            )
        )
        self.add_item(
            InputText(
                label="開始秒数",
                value=f"{BASE_SECONDS}",
                max_length=3,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        if self.children[1].value.isdecimal():
            tl = self.children[0].value
            start_seconds = int(self.children[1].value)
            conv_tl = change_time(tl, start_seconds)
            await interaction.response.send_message(
                content=f"TL秒数変換結果: {start_seconds}秒開始\n```c\n{conv_tl}```", ephemeral=True
            )
        else:
            await interaction.response.send_message("開始秒数の入力エラー", ephemeral=True)


class TLFormatModal(Modal):
    def __init__(self) -> None:
        super().__init__(title="TLフォーマット変換")

        self.add_item(
            InputText(
                label="TL (公式フォーマット)",
                placeholder="TL本文を貼り付けて下さい",
                style=discord.InputTextStyle.long,
                max_length=4000,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        tl = self.children[0].value
        fmt_tl = change_format(tl)
        await interaction.response.send_message(content=f"TLフォーマット変換結果\n```c\n{fmt_tl}```", ephemeral=True)


class TLLauncherView(discord.ui.View):
    def __init__(self, _logger: Logger):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)
        self.logger = _logger

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="秒数変換", custom_id="tl_conv")
    async def TLConvertButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push tl convert button. user.id: %s", interaction.user.id)
        modal = TLConvertModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.green, label="フォーマット変換", custom_id="tl_fmt")
    async def TLFormatButton(self, button, interaction: discord.Interaction):
        self.logger.debug("push tl format button. user.id: %s", interaction.user.id)
        modal = TLFormatModal()
        await interaction.response.send_modal(modal)


class TLCog(commands.Cog):
    def __init__(self, bot: BotClass):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(guild_ids=config.guild_ids, name="tl_conv", description="TLの秒数変換")
    async def TLConvertCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call tl convert command. author.id: %s", ctx.author.id)
        modal = TLConvertModal()
        await ctx.interaction.response.send_modal(modal)

    @TLConvertCommand.error
    async def TLConvertCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("tl convert command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="tl_fmt", description="TLのフォーマット変換")
    async def TLFormatCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call tl format command. author.id: %s", ctx.author.id)
        modal = TLFormatModal()
        await ctx.interaction.response.send_modal(modal)

    @TLFormatCommand.error
    async def TLFormatCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("tl format command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="tl_launcher", description="TLコマンドのランチャーを設置")
    async def TLLauncherCommand(self, ctx: discord.ApplicationContext):
        self.logger.info("call tl launcher command. author.id: %s", ctx.author.id)
        navigator = TLLauncherView(self.logger)
        embed = discord.Embed(title="TL変換ランチャー")
        embed.add_field(
            name="秒数変換",
            value=(
                "TLの秒数を指定した開始秒数に応じて変換する。\n" "元のTLは90秒開始想定としており、70秒と指定すれば20秒差し引かれた秒数に変換される。また120秒と指定すれば30秒足された秒数に変換される。"
            ),
            inline=False,
        )
        embed.add_field(name="フォーマット変換", value=("公式TLのフォーマットをちょっと見やすく変換する。\n" "同時刻のUBまとめと敵UBの表記を加工。"), inline=False)
        await ctx.respond(embed=embed, view=navigator)

    @TLLauncherCommand.error
    async def TLLauncherCommand_error(self, ctx: discord.ApplicationContext, error):
        self.logger.error("tl launcher command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    bot.add_cog(TLCog(bot))
    bot.persistent_view_classes.add(TLLauncherView)


def change_time(tl: str, seconds: int) -> str:
    lut = create_lut(BASE_SECONDS, seconds)
    conv_tl = re.sub("({})".format("|".join(map(re.escape, lut.keys()))), lambda m: lut[m.group()], tl)
    return conv_tl


def create_lut(base_seconds, changed_seconds):
    diff_seconds = base_seconds - changed_seconds
    lut_mm = {str_time_mm(i): str_time_mm(i - diff_seconds) for i in range(base_seconds + 1)}
    lut_m = {str_time_m(i): str_time_m(i - diff_seconds) for i in range(base_seconds + 1)}
    return lut_mm | lut_m


def str_time_m(seconds):
    if seconds >= 0:
        minutes = seconds // 60
        partial_seconds = seconds % 60
        return f"{minutes}:{partial_seconds:02}"
    else:
        minutes = -seconds // 60
        partial_seconds = -seconds % 60
        return f"-{minutes}:{partial_seconds:02}"


def str_time_mm(seconds):
    if seconds >= 0:
        minutes = seconds // 60
        partial_seconds = seconds % 60
        return f"{minutes:02}:{partial_seconds:02}"
    else:
        minutes = -seconds // 60
        partial_seconds = -seconds % 60
        return f"-{minutes:02}:{partial_seconds:02}"


def change_format(src_tl: str) -> str:
    fmt_tl = ""
    now_time = ""
    re_time = re.compile(r"^0[01]:\d{2}")
    re_ignore = re.compile(r"^バトル日時|^◆ユニオンバースト発動時間")
    for line in src_tl.splitlines():
        time_matchs = re_time.match(line)
        ignore_matchs = re_ignore.match(line)
        if time_matchs is not None:
            char_name = line.split(" ")[1]

            if char.is_boss(char_name):
                fmt_tl += "\n----- " + time_matchs[0][1:] + " ボスUB -----\n\n"
            else:
                if now_time == time_matchs[0][1:]:
                    fmt_tl += "    > "
                else:
                    fmt_tl += time_matchs[0][1:] + " "
                fmt_tl += " ".join(line.split(" ")[1:]) + "\n"
            now_time = time_matchs[0][1:]

        elif ignore_matchs is not None:
            fmt_tl += "\n"
        else:
            fmt_tl += line + "\n"

    return fmt_tl
