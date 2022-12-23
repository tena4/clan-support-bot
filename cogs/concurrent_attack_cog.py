import asyncio
import itertools
import math
import re
from datetime import datetime, timedelta
from logging import getLogger
from pyclbr import Function
from string import Template
from typing import Optional

import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.ui import InputText, Modal, Select, View

import app_config
import mongo_data as mongo
from log_decorator import ButtonLogDecorator, CallbackLogDecorator, CommandLogDecorator
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()
btn_log = ButtonLogDecorator(logger=logger)
cb_log = CallbackLogDecorator(logger=logger)
cmd_log = CommandLogDecorator(logger=logger)


class CancelUserSelect(Select):
    def __init__(self, message: discord.Message, replace_method: Function):
        atk_contents = message.content.splitlines()
        usernames = [re.findall(r"  (.*) 目標\d+万 :", atk)[0] for atk in atk_contents[2:]]
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

    @cb_log.log("submit a cancel user select")
    async def callback(self, interaction: discord.Interaction):
        refresh_message = await interaction.channel.fetch_message(self.message_id)
        repl_content = await self.replace_function(self.message_id, refresh_message.content, self.values)
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
        self.boss_str = atk_contents[0].split(" ")[0]
        target_attack = [atk for atk in atk_contents[2:] if re.search(rf"  {username} 目標\d+万 :", atk)][0]
        self.add_item(InputText(label=target_attack, placeholder="ダメージを入力して下さい"))

    @cb_log.log("submit a damage modal")
    async def callback(self, interaction: discord.Interaction):
        refresh_message = await interaction.channel.fetch_message(self.message_id)
        damage = self.children[0].value
        repl_content = await self.replace_function(
            self.message_id, refresh_message.content, [self.username], note=damage
        )
        await interaction.response.edit_message(content=repl_content)

        notify = mongo.ConcurrentAttackNotify.Get(guild_id=interaction.guild_id)
        if notify is not None and notify.level >= 3:
            attack = re.match(rf".*  {self.username} :", self.children[0].label).group()
            embed = discord.Embed(
                title="ダメージ入力しました。", fields=[discord.EmbedField(name=self.boss_str, value=f"{attack} {damage}")]
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            channel = interaction.guild.get_channel_or_thread(notify.channel_id)
            channel = channel if channel is not None else await interaction.guild.fetch_channel(notify.channel_id)
            await channel.send(embed=embed)


class TargetDamageModal(Modal):
    def __init__(self, message: discord.Message, username: str, attack_kind: str, replace_method: Function) -> None:
        super().__init__(title=f"{attack_kind} 目標ダメージ入力")
        self.username = username
        self.message_id = message.id
        self.replace_function = replace_method
        self.atk_content = message.content
        self.attack_kind = attack_kind
        self.add_item(InputText(label="ダメージ(万)", placeholder="1234"))

    @cb_log.log("submit a target damage modal")
    async def callback(self, interaction: discord.Interaction):
        repl_content = await self.replace_function(
            self.message_id,
            self.atk_content,
            [self.username],
            repl_atk=self.attack_kind,
            target_damage=int(self.children[0].value),
        )
        await interaction.response.edit_message(content=repl_content)

        notify = mongo.ConcurrentAttackNotify.Get(guild_id=interaction.guild_id)
        if notify is not None and notify.level >= 3:
            await self.send_attack_notify(
                notify_channel_id=notify.channel_id,
                content=repl_content,
                attack=self.attack_kind,
                interaction=interaction,
            )

    async def send_attack_notify(
        self, notify_channel_id: int, content: str, attack: str, interaction: discord.Interaction
    ):
        boss_match = re.match(r".* 残りHP", content)
        boss_str = boss_match.group().removesuffix(" 残りHP") if boss_match else "error"
        embed = discord.Embed(title=f"{boss_str} {attack}で登録しました。")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.guild.get_channel_or_thread(notify_channel_id)
        channel = channel if channel is not None else await interaction.guild.fetch_channel(notify_channel_id)
        await channel.send(embed=embed)


class AttackStartModal(Modal):
    def __init__(self, guild_id: int, members: list[discord.Member], boss_number: int, boss_name: str) -> None:
        super().__init__(title=f"{boss_number}ボス {boss_name} 同時凸開始")
        self.boss_number = boss_number
        self.mentions = " ".join([mem.mention for mem in members])
        temp_msg = mongo.TemplateAttackStartMessage.Get(guild_id=guild_id, boss_number=boss_number)
        if temp_msg:
            temp = Template(temp_msg.template)
            val_map = {"boss_number": boss_number, "boss_name": boss_name}
            msg = temp.safe_substitute(val_map)
            img_url = temp_msg.image_url
        else:
            msg = ""
            img_url = ""
        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label="開始メッセージ",
                value=msg,
                required=False,
            )
        )
        self.add_item(InputText(style=discord.InputTextStyle.singleline, label="画像URL", value=img_url, required=False))

    @cb_log.log("submit a attack start modal")
    async def callback(self, interaction: discord.Interaction):
        content = self.mentions
        embed = discord.Embed(title=self.title, description=self.children[0].value)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        if self.children[1].value:
            embed.set_image(url=self.children[1].value)
        notify = mongo.ConcurrentAttackNotify.Get(guild_id=interaction.guild_id)
        if notify is not None:
            await interaction.response.defer()
            if notify.level >= 1:
                channel = interaction.guild.get_channel_or_thread(notify.channel_id)
                channel = channel if channel is not None else await interaction.guild.fetch_channel(notify.channel_id)
                await channel.send(content=content, embed=embed)
        else:
            await interaction.response.send_message(content=content, embed=embed)

        guild = interaction.guild
        if guild is not None:
            event_title = f"{self.boss_number}ボス 同時凸中"
            already_event = next(filter(lambda se: se.name == event_title, guild.scheduled_events), None)
            if already_event is None:
                start_time = datetime.utcnow() + timedelta(minutes=1)
                end_time = start_time + timedelta(hours=1)
                event: Optional[discord.ScheduledEvent] = await guild.create_scheduled_event(
                    name=event_title, start_time=start_time, end_time=end_time, location=interaction.message.jump_url
                )
                if event is not None:
                    await event.start()


class UnfreezeModal(Modal):
    def __init__(self, guild_id: int, members: list[discord.Member], boss_number: int, boss_name: str) -> None:
        super().__init__(title=f"{boss_number}ボス {boss_name} 解凍")
        self.boss_number = boss_number
        self.mentions = " ".join([mem.mention for mem in members])
        temp_msg = mongo.TemplateUnfreezeMessage.Get(guild_id=guild_id, boss_number=boss_number)
        if temp_msg:
            temp = Template(temp_msg.template)
            val_map = {"boss_number": boss_number, "boss_name": boss_name}
            msg = temp.safe_substitute(val_map)
            img_url = temp_msg.image_url
        else:
            msg = ""
            img_url = ""
        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label="解凍メッセージ",
                value=msg,
                required=False,
            )
        )
        self.add_item(InputText(style=discord.InputTextStyle.singleline, label="画像URL", value=img_url, required=False))

    @cb_log.log("submit a unfreeze modal")
    async def callback(self, interaction: discord.Interaction):
        content = self.mentions
        embed = discord.Embed(title=self.title, description=self.children[0].value)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        if self.children[1].value:
            embed.set_image(url=self.children[1].value)
        notify = mongo.ConcurrentAttackNotify.Get(guild_id=interaction.guild_id)
        if notify is not None:
            await interaction.response.defer()
            if notify.level >= 1:
                channel = interaction.guild.get_channel_or_thread(notify.channel_id)
                channel = channel if channel is not None else await interaction.guild.fetch_channel(notify.channel_id)
                await channel.send(content=content, embed=embed)
        else:
            await interaction.response.send_message(content=content, embed=embed)

        guild = interaction.guild
        if guild is not None:
            event_title = f"{self.boss_number}ボス 同時凸中"
            already_event = next(filter(lambda se: se.name == event_title, guild.scheduled_events), None)
            if already_event is not None:
                await already_event.delete()


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
        repl_atk: Optional[str] = None,
        target_damage: Optional[int] = None,
        note: Optional[str] = None,
        is_change_battle_in: bool = False,
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
            content_lines = src_content.splitlines()
            atk_lines = content_lines[2:]
            for username in usernames:
                if is_change_battle_in:
                    atk_lines = change_battle_in(atk_lines, username)
                elif note is None:
                    atk_lines = replace_attacks(atk_lines, username, repl_atk, target_damage)
                else:
                    atk_lines = add_note(atk_lines, username, note)
            content_lines[2:] = atk_lines
            self.cache_contents[id] = "\n".join(content_lines)
            dst_content = self.cache_contents[id]
        return dst_content

    async def send_attack_notify(
        self, notify_channel_id: int, content: str, attack: str, interaction: discord.Interaction
    ):
        boss_match = re.match(r".* 残りHP", content)
        boss_str = boss_match.group().removesuffix(" 残りHP") if boss_match else "error"
        embed = discord.Embed(title=f"{boss_str} {attack}で登録しました。")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.guild.get_channel_or_thread(notify_channel_id)
        channel = channel if channel is not None else await interaction.guild.fetch_channel(notify_channel_id)
        await channel.send(embed=embed)

    async def send_cancel_notify(self, notify_channel_id: int, content: str, interaction: discord.Interaction):
        boss_match = re.match(r".* 残りHP", content)
        boss_str = boss_match.group().removesuffix(" 残りHP") if boss_match else "error"
        embed = discord.Embed(title=f"{boss_str} キャンセルしました。")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.guild.get_channel_or_thread(notify_channel_id)
        channel = channel if channel is not None else await interaction.guild.fetch_channel(notify_channel_id)
        await channel.send(embed=embed)

    @discord.ui.select(
        placeholder="凸内容を選択",
        custom_id="attack_select",
        options=[
            discord.SelectOption(label="新凸 物理", emoji="🗡️", value="　新凸　 物🗡️"),
            discord.SelectOption(label="新凸 魔法", emoji="✡️", value="　新凸　 魔✡️"),
            discord.SelectOption(label="持越 物理", emoji="🗡️", value="★持越★ 物🗡️"),
            discord.SelectOption(label="持越 魔法", emoji="✡️", value="★持越★ 魔✡️"),
        ],
    )
    async def AttackSelectCallback(self, select: discord.ui.Select, interaction: discord.Interaction):
        attack_kind = select.values[0]
        modal = TargetDamageModal(
            interaction.message, interaction.user.display_name, attack_kind, self.sync_replace_content
        )
        await interaction.response.send_modal(modal=modal)

    # custom_id is required and should be unique for <commands.Bot.add_view>
    # attribute emoji can be used to include emojis which can be default str emoji or str(<:emojiName:int(ID)>)
    # timeout can be used if there is a timeout on the button interaction. Default timeout is set to 180.
    @discord.ui.button(style=discord.ButtonStyle.blurple, label="本戦", emoji="✈️", custom_id="declaration", row=2)
    @btn_log.log("push declaration button")
    async def DeclarationButton(self, button, interaction: discord.Interaction):
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
            is_change_battle_in=True,
        )
        await interaction.response.edit_message(content=repl_content)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="ダメ入力", emoji="📝", custom_id="input_damage", row=2)
    @btn_log.log("push input damage attack button")
    async def InputDamageButton(self, button, interaction: discord.Interaction):
        atk_list = interaction.message.content.splitlines()
        username = interaction.user.display_name
        matches = [atk for atk in atk_list[2:] if re.search(rf"  {username} 目標\d+万 :", atk)]
        if len(matches) == 1:
            modal = DamageModal(interaction.message, username, self.sync_replace_content)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("対象凸がありません。", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.red, label="取消", emoji="🚮", custom_id="cancel_attack", row=2)
    @btn_log.log("push cancel attack button")
    async def CancelAttackButton(self, button, interaction: discord.Interaction):
        repl_content = await self.sync_replace_content(
            interaction.message.id,
            interaction.message.content,
            [interaction.user.display_name],
        )
        await interaction.response.edit_message(content=repl_content)
        notify = mongo.ConcurrentAttackNotify.Get(guild_id=interaction.guild_id)
        if notify is not None and notify.level >= 3:
            await self.send_cancel_notify(
                notify_channel_id=notify.channel_id, content=repl_content, interaction=interaction
            )

    @discord.ui.button(style=discord.ButtonStyle.green, label="同凸開始", emoji="📢", custom_id="attack_start", row=3)
    @btn_log.log("push attack start button")
    async def AttackStartButton(self, button, interaction: discord.Interaction):
        atk_list = interaction.message.content.splitlines()
        members = get_attack_members(atk_list[2:], interaction.guild)
        boss_content = atk_list[0].split(" ")[0]
        boss_number = int(boss_content.split(":")[0])
        boss_name = boss_content.split(":")[1]
        modal = AttackStartModal(
            guild_id=interaction.guild_id, members=members, boss_number=boss_number, boss_name=boss_name
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.green, label="解凍", emoji="🔥", custom_id="unfreeze", row=3)
    @btn_log.log("push unfreeze button")
    async def UnfreezeButton(self, button, interaction: discord.Interaction):
        atk_list = interaction.message.content.splitlines()
        members = get_attack_members(atk_list[2:], interaction.guild)
        boss_content = atk_list[0].split(" ")[0]
        boss_number = int(boss_content.split(":")[0])
        boss_name = boss_content.split(":")[1]
        modal = UnfreezeModal(
            guild_id=interaction.guild_id, members=members, boss_number=boss_number, boss_name=boss_name
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(style=discord.ButtonStyle.gray, label="代消", emoji="☢️", custom_id="proxy_cancel_attack", row=3)
    @btn_log.log("push proxy cancel attack button")
    async def ProxyCancelAttackButton(self, button, interaction: discord.Interaction):
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
    level_desc = "通知レベル(0~3) 高いほど通知量が多い"
    template_desc = "メッセージのテンプレート"
    img_url_desc = "画像のURL"

    def __init__(self, bot: BotClass):
        self.bot = bot

    @slash_command(guild_ids=config.guild_ids, name="concurrent_atk", description="同時凸のテンプレートを作成する")
    @cmd_log.info("call concurrent attack command")
    async def ConcurrentAttackCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        hp: Option(int, hp_desc, required=False, default=None),
    ):
        navigator = ConcurrentAttackButtonView()
        boss = mongo.BossInfo.Get(number=boss_num)
        if boss is None:
            await ctx.respond(f"{boss_num}ボス情報が登録されていません。", ephemeral=True)
            return
        boss_hp = hp if hp is not None else boss.hp
        await ctx.respond(f"{boss.number}:{boss.name} 残りHP(万):{boss_hp}\n------", view=navigator)

    @ConcurrentAttackCommand.error
    @cmd_log.error("concurrent attack command error")
    async def ConcurrentAttackCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

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
    @cmd_log.error("calc carry over time command error")
    async def CalcCarryOverTimeCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="notify_concurrent_atk_register", description="同時凸の通知を登録する")
    @cmd_log.info("call notify concurrent attack regisuter command")
    async def NotifyConcurrentAttackRegisterCommand(
        self,
        ctx: discord.ApplicationContext,
        level: Option(int, level_desc, choices=[0, 1, 2, 3]),
    ):
        mongo.ConcurrentAttackNotify(guild_id=ctx.guild_id, channel_id=ctx.channel_id, level=level).Set()
        await ctx.respond(f"このチャンネルに同時凸の通知(level={level})を登録しました。", ephemeral=True)

    @NotifyConcurrentAttackRegisterCommand.error
    @cmd_log.error("call notify concurrent attack regisuter command error")
    async def NotifyConcurrentAttackRegisterCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="notify_concurrent_atk_unregister", description="同時凸の通知を登録解除する")
    @cmd_log.info("call notify concurrent attack unregister command")
    async def NotifyConcurrentAttackUnregisterCommand(self, ctx: discord.ApplicationContext):
        notify = mongo.ConcurrentAttackNotify.Get(guild_id=ctx.guild_id)
        if notify is not None:
            notify.Delete()
            await ctx.respond(f"同時凸の通知(channel=<#{notify.channel_id}>)を登録解除しました。", ephemeral=True)
        else:
            await ctx.respond("このサーバーに同時凸の通知は登録されていません。", ephemeral=True)

    @NotifyConcurrentAttackUnregisterCommand.error
    @cmd_log.error("call notify concurrent attack unregister command error")
    async def NotifyConcurrentAttackUnregisterCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="set_unfreeze_template", description="解凍メッセージのテンプレートを設定する")
    @cmd_log.info("call set unfreeze template command")
    async def SetUnfreezeTemplateCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_number: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        template: Option(str, template_desc),
        img_url: Option(str, img_url_desc),
    ):
        mongo.TemplateUnfreezeMessage(
            guild_id=ctx.guild_id, boss_number=boss_number, template=template, image_url=img_url
        ).Set()
        await ctx.respond(f"解凍メッセージ({boss_number}ボス)のテンプレートの設定をしました。", ephemeral=True)

    @SetUnfreezeTemplateCommand.error
    @cmd_log.error("call set unfreeze template command error")
    async def SetUnfreezeTemplateCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="remove_unfreeze_template", description="解凍メッセージのテンプレート設定を削除する")
    @cmd_log.info("call remove unfreeze template command")
    async def RemoveUnfreezeTemplateCommand(
        self, ctx: discord.ApplicationContext, boss_number: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5])
    ):
        temp_msg = mongo.TemplateUnfreezeMessage.Get(guild_id=ctx.guild_id, boss_number=boss_number)
        if temp_msg is not None:
            temp_msg.Delete()
            await ctx.respond(f"解凍メッセージ({boss_number}ボス)のテンプレートの設定を削除しました。", ephemeral=True)
        else:
            await ctx.respond(f"解凍メッセージ({boss_number}ボス)のテンプレートの設定がされていません。", ephemeral=True)

    @RemoveUnfreezeTemplateCommand.error
    @cmd_log.error("call remove unfreeze template command error")
    async def RemoveUnfreezeTemplateCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="set_attack_start_template", description="凸開始メッセージのテンプレートを設定する")
    @cmd_log.info("call set attack start template command")
    async def SetAttackStartTemplateCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_number: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        template: Option(str, template_desc),
        img_url: Option(str, img_url_desc),
    ):
        mongo.TemplateAttackStartMessage(
            guild_id=ctx.guild_id, boss_number=boss_number, template=template, image_url=img_url
        ).Set()
        await ctx.respond(f"凸開始メッセージ({boss_number}ボス)のテンプレートの設定をしました。", ephemeral=True)

    @SetAttackStartTemplateCommand.error
    @cmd_log.error("call set attack start template command error")
    async def SetAttackStartTemplateCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(
        guild_ids=config.guild_ids, name="remove_attack_start_template", description="凸開始メッセージのテンプレート設定を削除する"
    )
    @cmd_log.info("call remove attack start template command")
    async def RemoveAttackStartTemplateCommand(
        self, ctx: discord.ApplicationContext, boss_number: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5])
    ):
        temp_msg = mongo.TemplateUnfreezeMessage.Get(guild_id=ctx.guild_id, boss_number=boss_number)
        if temp_msg is not None:
            temp_msg.Delete()
            await ctx.respond(f"凸開始メッセージ({boss_number}ボス)のテンプレートの設定を削除しました。", ephemeral=True)
        else:
            await ctx.respond(f"凸開始メッセージ({boss_number}ボス)のテンプレートの設定がされていません。", ephemeral=True)

    @RemoveAttackStartTemplateCommand.error
    @cmd_log.error("call remove attack start template command error")
    async def RemoveAttackStartTemplateCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(ConcurrentAttackCog(bot))
    bot.persistent_view_classes.add(ConcurrentAttackButtonView)


def change_battle_in(atk_list: list[str], username: str) -> list[str]:
    target_indexes = [i for i, atk in enumerate(atk_list) if re.search(rf"  {username} 目標\d+万 :.*", atk)]
    for i in target_indexes:
        is_battle_in = bool(re.match(rf"本戦 (　新凸　|★持越★).*  {username} 目標\d+万 :", atk_list[i]))
        if is_battle_in:
            atk = re.search(rf"(　新凸　|★持越★).*  {username} 目標\d+万 :.*$", atk_list[i]).group()
            atk_list[i] = f"{atk}"
        else:
            atk_list[i] = "本戦 " + atk_list[i]
    return atk_list


def replace_attacks(
    atk_list: list[str], username: str, repl_atk: Optional[str], target_damage: Optional[int]
) -> list[str]:
    repl_atk_list = [atk for atk in atk_list if not re.search(rf"  {username} 目標\d+万 :.*", atk)]
    if repl_atk is not None:
        repl_atk_list.append(f"{repl_atk}  {username} 目標{target_damage}万 :")
    return repl_atk_list


def add_note(atk_list: list[str], username: str, note: str) -> list[str]:
    target_indexes = [i for i, atk in enumerate(atk_list) if re.search(rf"  {username} 目標\d+万 :", atk)]
    for i in target_indexes:
        atk = re.match(rf".*  {username} 目標\d+万 :", atk_list[i]).group()
        atk_list[i] = f"{atk} {note}"
    sorted_atk_list = sort_by_damage(atk_list)
    return sorted_atk_list


def sort_by_damage(atk_list: list[str]) -> list[str]:
    atks = [(atk, re.search(r"万 : .+$", atk)) for atk in atk_list]
    atks_with_note = [(atk, re.search(r"\d{3,}", note.group())) for atk, note in atks if note is not None]
    atks_with_dmg = [(atk, int(dmg.group())) for atk, dmg in atks_with_note if dmg is not None]
    atks_with_dmg.sort(key=lambda a: a[1], reverse=True)
    sorted_atks = [atk for atk, _ in atks_with_dmg]
    atks_without_dmg = [atk for atk in atk_list if atk not in sorted_atks]
    sorted_atks += atks_without_dmg
    return sorted_atks


def get_attack_members(atk_list: list[str], guild: discord.Guild) -> list[str]:
    user_names = [re.findall(r"  (.+) 目標\d+万 :", atk)[0] for atk in atk_list if re.search(r"  .+ 目標\d+万 :", atk)]
    members = [guild.get_member_named(u) for u in user_names]
    members = [m for m in members if m is not None]
    return members


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
