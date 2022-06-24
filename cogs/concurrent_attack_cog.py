import asyncio
import itertools
import math
import re
from logging import getLogger
from pyclbr import Function
from typing import Optional

import app_config
import discord
import postgres_helper as pg
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.ui import InputText, Modal, Select, View
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()


class CancelUserSelect(Select):
    def __init__(self, message: discord.Message, replace_method: Function):
        atk_contents = message.content.splitlines()
        usernames = [re.search("  .* :", atk).group().strip(" :") for atk in atk_contents[2:]]
        options = [discord.SelectOption(label=u) for u in usernames]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            custom_id="proxy_cancel_attack_select",
            placeholder="Choose your favourite colour...",
            min_values=0,
            max_values=len(options),
            options=options,
        )
        self.message_id = message.id
        self.replace_function = replace_method

    async def callback(self, interaction: discord.Interaction):
        logger.info(
            "submit a cancel user select",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        refresh_message = await interaction.channel.fetch_message(self.message_id)
        repl_content = await self.replace_function(self.message_id, refresh_message.content, self.values, None)
        await refresh_message.edit(content=repl_content)
        await interaction.response.send_message(
            content="下記ユーザーの凸をキャンセルしました。\n{}".format("\n".join(self.values)), ephemeral=True
        )


class ProxyCancelView(View):
    def __init__(self, message, replace_method):
        super().__init__(timeout=120)
        self.add_item(CancelUserSelect(message, replace_method))


class DamageModal(Modal):
    def __init__(self, message: discord.Message, username: str, replace_method: Function) -> None:
        super().__init__(title="ダメージ入力")
        self.username = username
        self.message_id = message.id
        self.replace_function = replace_method
        atk_contents = message.content.splitlines()
        target_attack = [atk for atk in atk_contents[2:] if re.match(rf".*\s{username} :", atk)][0]
        self.add_item(InputText(label=target_attack, placeholder="ダメージを入力して下さい"))

    async def callback(self, interaction: discord.Interaction):
        logger.info(
            "submit a damage modal",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        refresh_message = await interaction.channel.fetch_message(self.message_id)
        damage = self.children[0].value
        repl_content = await self.replace_function(
            self.message_id, refresh_message.content, [self.username], None, damage
        )
        await interaction.response.edit_message(content=repl_content)


class ConcurrentAttackButtonView(View):
    def __init__(self):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)
        self.lock_lock = asyncio.Lock()
        self.replace_locks = {}
        self.cache_contents = {}

    async def sync_replace_content(
        self,
        id: int,
        src_content: str,
        usernames: list[str],
        repl_atk: Optional[str],
        note: Optional[str] = None,
    ) -> str:
        async with self.lock_lock:
            lock = self.replace_locks.get(id)
            if lock is None:
                lock = asyncio.Lock()
                self.replace_locks[id] = lock

        async with lock:
            cache_content = self.cache_contents.get(id)
            if cache_content is not None and src_content != cache_content:
                src_content = cache_content
            atk_contents = src_content.splitlines()
            for username in usernames:
                if note is None:
                    atk_contents = replace_attacks(atk_contents, username, repl_atk)
                else:
                    atk_contents = add_note(atk_contents, username, note)
            self.cache_contents[id] = "\n".join(atk_contents)
            dst_content = self.cache_contents[id]
        return dst_content

    # custom_id is required and should be unique for <commands.Bot.add_view>
    # attribute emoji can be used to include emojis which can be default str emoji or str(<:emojiName:int(ID)>)
    # timeout can be used if there is a timeout on the button interaction. Default timeout is set to 180.
    @discord.ui.button(
        style=discord.ButtonStyle.blurple, label="新凸:物", emoji="\N{Dagger Knife}", custom_id="new_physics_attack"
    )
    async def NewPhysicsAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push new physics attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            "　新凸　 物\N{Dagger Knife}",
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(
        style=discord.ButtonStyle.blurple, label="新凸:魔", emoji="\N{Star Of David}", custom_id="new_magic_attack"
    )
    async def NewMagicAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push new magic attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            "　新凸　 魔\N{Star Of David}",
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(
        style=discord.ButtonStyle.green, label="持越:物", emoji="\N{Dagger Knife}", custom_id="carry_physics_attack"
    )
    async def CarryOverPhysicsAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push carry over physics attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            "★持越★ 物\N{Dagger Knife}",
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(
        style=discord.ButtonStyle.green, label="持越:魔", emoji="\N{Star Of David}", custom_id="carry_magic_attack"
    )
    async def CarryOverMagicAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push carry over magic attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            "★持越★ 魔\N{Star Of David}",
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="ダメージ入力", custom_id="input_damage")
    async def InputDamageButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push input damage attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        atk_list = interaction.message.content.splitlines()
        username = interaction.user.display_name
        matches = [atk for atk in atk_list[2:] if re.match(rf".*\s{username} :", atk)]
        if len(matches) == 1:
            modal = DamageModal(interaction.message, username, self.sync_replace_content)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("対象凸がありません。", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="cancel_attack")
    async def CancelAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push cancel attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            None,
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="代理キャンセル", custom_id="proxy_cancel_attack")
    async def ProxyCancelAttackButton(self, button, interaction: discord.Interaction):
        logger.info(
            "push proxy cancel attack button",
            extra={
                "channel_id": interaction.channel_id,
                "message_id": interaction.message.id if interaction.message else None,
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        atk_list = interaction.message.content.splitlines()
        if len(atk_list) <= 2:
            return await interaction.response.defer()

        pcview = ProxyCancelView(interaction.message, self.sync_replace_content)
        resp_msg = await interaction.response.send_message(
            content="キャンセルする凸のユーザーを選択して下さい(複数可)", view=pcview, ephemeral=True
        )

        async def child_view_timeout():
            await resp_msg.edit_original_message(content="インタラクションがタイムアウトしました。本メッセージは削除して下さい。")
            pcview.stop()

        pcview.on_timeout = child_view_timeout


class ConcurrentAttackCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    hp_desc = "ボスの残りHP(万)"
    dmg_desc = "ダメージ(万)"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="concurrent_atk", description="同時凸のテンプレートを作成する")
    async def ConcurrentAttackCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        hp: Option(int, hp_desc, required=False, default=None),
    ):
        logger.info(
            "call concurrent attack command",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
            },
        )
        navigator = ConcurrentAttackButtonView()
        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond(f"{boss_num}ボス情報が登録されていません。", ephemeral=True)
            return
        boss_hp = hp if hp is not None else boss.hp
        await ctx.respond(f"{boss.number}:{boss.name} 残りHP(万):{boss_hp}\n------", view=navigator)

    @ConcurrentAttackCommand.error
    async def ConcurrentAttackCommand_error(self, ctx: discord.ApplicationContext, error):
        logger.error(
            "concurrent attack command error",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
                "error": error,
            },
        )
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="carry_over", description="同時凸時の持ち越し時間の算出")
    async def CalcCarryOverTimeCommand(
        self,
        ctx: discord.ApplicationContext,
        hp: Option(int, hp_desc, required=True),
        dmg1: Option(int, dmg_desc, required=True),
        dmg2: Option(int, dmg_desc, required=False, default=None),
        dmg3: Option(int, dmg_desc, required=False, default=None),
        dmg4: Option(int, dmg_desc, required=False, default=None),
    ):
        logger.info(
            "call calc carry over time command",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
            },
        )
        input_dmgs = [dmg1]
        if dmg2 is not None:
            input_dmgs.append(dmg2)
        if dmg3 is not None:
            input_dmgs.append(dmg3)
        if dmg4 is not None:
            input_dmgs.append(dmg4)

        resluts = calc_carry_over_permutations(hp, input_dmgs)
        resluts.sort(key=lambda x: x[0], reverse=True)
        resluts_str = ["```c"]
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
            if rst_str not in resluts_str:
                resluts_str.append(rst_str)
        resluts_str.append("```")
        embed = discord.Embed(title="持ち越し時間算出")
        embed.add_field(name=f"残りボスHP(万):{hp}", value="\n".join(resluts_str))
        await ctx.respond(embed=embed)

    @CalcCarryOverTimeCommand.error
    async def CalcCarryOverTimeCommand_error(self, ctx: discord.ApplicationContext, error):
        logger.error(
            "calc carry over time command error",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
                "error": error,
            },
        )
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(ConcurrentAttackCog(bot))
    bot.persistent_view_classes.add(ConcurrentAttackButtonView)


def replace_attacks(atk_list: list[str], username: str, repl_atk: Optional[str]) -> list[str]:
    repl_atk_list = [atk for atk in atk_list if not re.match(rf".*\s{username} :.*", atk)]
    if repl_atk is not None:
        repl_atk_list.append(f"{repl_atk}  {username} :")
    return repl_atk_list


def add_note(atk_list: list[str], username: str, note: str):
    target_indexes = [i for i, atk in enumerate(atk_list) if re.match(rf".*\s{username} :", atk)]
    for i in target_indexes:
        atk = re.match(rf".*\s{username} :", atk_list[i]).group()
        atk_list[i] = f"{atk} {note}"
    return atk_list


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
