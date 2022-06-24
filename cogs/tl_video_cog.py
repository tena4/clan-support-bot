import asyncio
import re
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from logging import getLogger

import app_config
import discord
import postgres_helper as pg
from discord.commands import Option, slash_command
from discord.ext import commands, tasks
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mybot import BotClass

logger = getLogger(__name__)
config = app_config.Config.get_instance()

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
IGNORE_WORDS = ["Ark", "このファン", "コノファン"]


class TLVideoCog(commands.Cog):
    boss_num_desc = "ボスの番号"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.task_count = 0
        self.msg = None
        self.enabled = len(config.youtube_api_keys) > 0
        if self.enabled:
            self.get_api_key = select_api_key()
            self.cached_embeds: dict[int, (str, list[discord.Embed])] = {i: () for i in range(1, 6)}
            self.scheduled_tl_search.start()

    def cog_unload(self):
        self.scheduled_tl_search.cancel()

    @tasks.loop(minutes=30.0)
    async def scheduled_tl_search(self):
        logger.info("run scheduled tl search")
        bosses = pg.get_bosses_info()
        for boss in bosses:
            await asyncio.sleep(10)
            query = f"{boss.name} 段階目 -1段階目 -2段階目 -3段階目"
            api_key = self.get_api_key()
            try:
                logger.debug(f'youtube search. query: "{query}"')
                videos = youtube_search(query, api_key)
            except HttpError as e:
                logger.warn("An HTTP error %d occurred:\n%s", e.resp.status, e.content)
                break

            other_boss_names = [b.name for b in bosses if b.name not in boss.name]
            boss_regex = re.compile(boss.name)
            ignore_boss_regex = re.compile("|".join(other_boss_names))
            ignore_words_regex = re.compile("|".join(IGNORE_WORDS))
            videos = [
                v
                for v in videos
                if boss_regex.search(v.title) is not None
                and ignore_boss_regex.search(v.title) is None
                and ignore_words_regex.search(v.title) is None
                and v.damage > 0
            ]

            videos.sort(key=lambda x: x.damage, reverse=True)
            updated_at = datetime.now(timezone(timedelta(hours=9)))
            updated_at_str = updated_at.strftime("%Y/%m/%d %H:%M:%S")
            content = f"TL動画対象ボス: {boss.name}\n最終更新日時: {updated_at_str}\nヒット件数: {len(videos)}, ダメージ上位10件を表示"

            embeds = [create_video_embed(v, updated_at) for v in videos[:10]]
            self.cached_embeds[boss.number] = (content, embeds)

            subsc_msgs = pg.get_subsc_messages(boss.number)
            err_msgs: list[pg.SubscMessage] = []
            for msg in subsc_msgs:
                await asyncio.sleep(1)
                try:
                    guild = self.bot.get_guild(msg.guild_id)
                    if guild is None:
                        guild = await self.bot.fetch_guild(msg.guild_id)
                    channel = guild.get_channel(msg.channel_id)
                    if channel is None:
                        channel = await guild.fetch_channel(msg.channel_id)
                    fmsg = await channel.fetch_message(msg.message_id)

                    await fmsg.edit(content=content, embeds=embeds)
                except discord.NotFound:
                    err_msgs.append(msg)
                except HTTPException:
                    logger.error(
                        "HTTP exception by edit subscribe message",
                        exc_info=True,
                        extra={
                            "channel_id": msg.channel_id,
                            "message_id": msg.message_id,
                        },
                    )
                except Exception:
                    logger.error(
                        "unknown exceptions by edit subscribe message",
                        exc_info=True,
                        extra={
                            "channel_id": msg.channel_id,
                            "message_id": msg.message_id,
                        },
                    )

            for em in err_msgs:
                # 編集するメッセージがない(削除された)場合、subsc_msgsから当メッセージを外す
                logger.info(
                    "remove message subscriber",
                    extra={
                        "channel_id": em.channel_id,
                        "message_id": em.message_id,
                    },
                )
                pg.delete_subsc_message(em.guild_id, em.channel_id, em.message_id)

            gotten_list = [g.video_id for g in pg.get_tl_video_gotten_list()]
            yet_list = [(i, v) for i, v in enumerate(videos) if v.vid not in gotten_list]
            if len(yet_list) == 0:
                continue
            notice_content = "TL動画対象ボス: {}\n通知時ダメージ順位: [{}]".format(
                boss.name, ", ".join([f"**{str(i + 1)}**" if i <= 2 else str(i + 1) for i, _ in yet_list])
            )
            notice_video_embeds = [create_video_embed(v, updated_at) for _, v in yet_list]
            pg.set_tl_video_gotten_list([v.vid for _, v in yet_list])
            notify_list = pg.get_tl_video_notify_list()
            err_chs: list[pg.TLVideoNotify] = []
            for notify in notify_list:
                await asyncio.sleep(1)
                try:
                    guild = self.bot.get_guild(notify.guild_id)
                    if guild is None:
                        guild = await self.bot.fetch_guild(notify.guild_id)
                    channel = guild.get_channel(notify.channel_id)
                    if channel is None:
                        channel = await guild.fetch_channel(notify.channel_id)
                    await channel.send(content=notice_content, embeds=notice_video_embeds[:10])
                except discord.NotFound:
                    err_chs.append(msg)
                except HTTPException:
                    logger.error(
                        "HTTP exception by notify new tl video",
                        exc_info=True,
                        extra={
                            "channel_id": notify.channel_id,
                        },
                    )
                except Exception:
                    logger.error(
                        "unknown exceptions by notify new tl video",
                        exc_info=True,
                        extra={
                            "channel_id": notify.channel_id,
                        },
                    )

            for err_ch in err_chs:
                # チャンネルがない(削除された)場合、ti_video_notifyから当チャンネルを外す
                logger.info(
                    "remove tl video notify",
                    extra={
                        "channel_id": err_ch.channel_id,
                    },
                )
                pg.remove_tl_video_notify(err_ch.guild_id, err_ch.channel_id)

    @slash_command(guild_ids=config.guild_ids, name="list_tl", description="定期的なTL動画のリストアップ(30分毎に更新)")
    async def ListTLVideosCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
    ):
        logger.info(
            "call list tl videos command",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
            },
        )
        if not self.enabled:
            logger.warn(
                "Misconfiguration of YOUTUBE_API_KEY environment variable",
                extra={
                    "channel_id": ctx.channel_id,
                    "user_id": ctx.user.id if ctx.user else None,
                },
            )
            await ctx.respond("環境変数の設定が正しくされていません。(YOUTUBE_API_KEY)", ephemeral=True)
            return

        boss = pg.get_boss_info(boss_num)
        if boss is None:
            logger.warn(
                "Misconfiguration of boss info resiger",
                extra={
                    "channel_id": ctx.channel_id,
                    "user_id": ctx.user.id if ctx.user else None,
                },
            )
            await ctx.respond(f"{boss_num}ボスの情報が登録されていません。", ephemeral=True)
            return

        if self.cached_embeds[boss.number] == ():
            content = f"TL動画リスト: {boss.name}\n次の定期更新までお待ちください。"
            interact: discord.Interaction = await ctx.respond(content)
            msg = await interact.original_message()
            pg.set_subsc_message(msg.guild.id, msg.channel.id, msg.id, boss.number)
        else:
            content, embeds = self.cached_embeds[boss.number]
            interact: discord.Interaction = await ctx.respond(content, embeds=embeds)
            msg = await interact.original_message()
            pg.set_subsc_message(msg.guild.id, msg.channel.id, msg.id, boss.number)

    @ListTLVideosCommand.error
    async def ListTLVideosCommand_error(self, ctx: discord.ApplicationContext, error):
        logger.error(
            "list tl videos command error",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
                "error": error,
            },
        )
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="list_tl_notify_register", description="TL動画の新着通知を登録")
    async def ListTLVideosNotifyRegisterCommand(self, ctx: discord.ApplicationContext):
        logger.info(
            "call list tl videos notify register command",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
            },
        )
        notify_list = pg.get_tl_video_notify_list()
        if pg.TLVideoNotify(ctx.guild_id, ctx.channel_id) not in notify_list:
            pg.set_tl_video_notify(guild_id=ctx.guild_id, channel_id=ctx.channel_id)
            return await ctx.respond("通知登録しました。")
        else:
            return await ctx.respond("既に登録されています。", ephemeral=True)

    @ListTLVideosNotifyRegisterCommand.error
    async def ListTLVideosNotifyRegisterCommand_error(self, ctx: discord.ApplicationContext, error):
        logger.error(
            "list tl videos notify register command error",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
                "error": error,
            },
        )
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="list_tl_notify_unregister", description="TL動画の新着通知を登録")
    async def ListTLVideosNotifyUnregisterCommand(self, ctx: discord.ApplicationContext):
        logger.info(
            "call list tl videos notify unregister command",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
            },
        )
        notify_list = pg.get_tl_video_notify_list()
        if pg.TLVideoNotify(ctx.guild_id, ctx.channel_id) in notify_list:
            pg.remove_tl_video_notify(guild_id=ctx.guild_id, channel_id=ctx.channel_id)
            return await ctx.respond("通知登録を解除しました。")
        else:
            return await ctx.respond("登録されていません。", ephemeral=True)

    @ListTLVideosNotifyUnregisterCommand.error
    async def ListTLVideosNotifyUnregisterCommand_error(self, ctx: discord.ApplicationContext, error):
        logger.error(
            "list tl videos notify unregister command error",
            extra={
                "channel_id": ctx.channel_id,
                "user_id": ctx.user.id if ctx.user else None,
                "error": error,
            },
        )
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot: BotClass):
    logger.info("Load bot cog from %s", __name__)
    bot.add_cog(TLVideoCog(bot))


def timedelta_color(delta: timedelta) -> discord.Colour:
    if delta.days > 0:
        return discord.Colour.green()
    elif delta.seconds > 7200:
        return discord.Colour.yellow()
    elif delta.seconds > 1800:
        return discord.Colour.red()
    elif delta.seconds >= 0:
        return discord.Colour.purple()
    else:
        return discord.Colour.light_grey()


class TLVideo:
    def __init__(self, youtube_item) -> None:
        self.title = youtube_item["snippet"]["title"]
        self.vid = youtube_item["id"]["videoId"]
        self.description = self.__shortening_description(youtube_item["snippet"]["description"])
        self.channel_title = youtube_item["snippet"]["channelTitle"]
        self.published_at = datetime.fromisoformat(youtube_item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        self.thumbnail_url = youtube_item["snippet"]["thumbnails"]["default"]["url"]
        self.damage = self.__get_damage()

    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.vid}"

    def __get_damage(self):
        ext_dmgs = re.findall(r"\d[,\d]{1,2}\d{2,}(?![年s])", self.title)
        if len(ext_dmgs) > 0:
            return max([int(re.sub("[,]", "", d)) for d in ext_dmgs])
        else:
            return -1

    def __shortening_description(self, desc):
        return re.sub(r"https://discordapp.com/channels/[/\d]+", "https://discordapp.com/channels/...", desc)


def create_video_embed(video: TLVideo, updated_at: datetime) -> discord.Embed:
    pub_at_jp = video.published_at.astimezone(timezone(timedelta(hours=9)))
    pub_at_jp_str = pub_at_jp.strftime("%Y/%m/%d %H:%M:%S")
    embed = discord.Embed(
        title=video.title,
        url=video.url(),
        color=timedelta_color(updated_at - pub_at_jp),
    )
    embed.add_field(name="ダメージ", value=f"{video.damage}万")
    embed.add_field(name="チャンネル", value=video.channel_title)
    embed.add_field(name="投稿日時", value=pub_at_jp_str)
    embed.set_footer(text=video.description)
    embed.set_thumbnail(url=video.thumbnail_url)
    return embed


def select_api_key():
    cnt = 0

    def key_next():
        nonlocal cnt
        idx = cnt % len(config.youtube_api_keys)
        cnt += 1
        return config.youtube_api_keys[idx]

    return key_next


def youtube_search(query: str, api_key: str, page_token=None) -> list[TLVideo]:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)
    published_after = datetime.now() - timedelta(days=10.0)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = (
        youtube.search()
        .list(
            q=query,
            part="id,snippet",
            publishedAfter=published_after.isoformat() + "Z",
            order="date",
            type="video",
            maxResults=50,
            pageToken=page_token,
        )
        .execute()
    )

    videos = [
        TLVideo(result) for result in search_response.get("items", []) if result["id"]["kind"] == "youtube#video"
    ]

    next_page_token = search_response.get("nextPageToken")
    if next_page_token:
        next_videos = youtube_search(query=query, api_key=api_key, page_token=next_page_token)
        videos += next_videos

    return videos
