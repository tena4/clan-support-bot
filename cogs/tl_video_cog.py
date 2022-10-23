import asyncio
import re
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from logging import ERROR, getLogger
from typing import Optional

import app_config
import char
import discord
import mongo_helper as mongo
from discord.commands import Option, slash_command
from discord.ext import commands, tasks
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from log_decorator import CommandLogDecorator
from mybot import BotClass

getLogger("googleapiclient.discovery_cache").setLevel(ERROR)
logger = getLogger(__name__)
config = app_config.Config.get_instance()
cmd_log = CommandLogDecorator(logger=logger)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
IGNORE_WORDS = ["Ark", "このファン", "コノファン", "2段階目", "3段階目"]


class TLVideoCog(commands.Cog):
    boss_num_desc = "ボスの番号"
    is_carry_over_desc = "持ち越し用"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.task_count = 0
        self.msg = None
        self.enabled = len(config.youtube_api_keys) > 0
        if self.enabled:
            self.get_api_key = select_api_key()
            self.cached_embeds: dict[str, (str, list[discord.Embed])] = {f"{i//2}_{i%2}": () for i in range(2, 12)}
            self.scheduled_tl_search.start()

    def cog_unload(self):
        self.scheduled_tl_search.cancel()

    @tasks.loop(minutes=30.0)
    async def scheduled_tl_search(self):
        logger.info("run scheduled tl search")
        bosses = mongo.BossInfo.Gets()
        query = "({}) (段階目 | パーティ編成)".format(" | ".join([f"intitle:{b.name}" for b in bosses]))
        api_key = self.get_api_key()
        search_pub_before = datetime.now(timezone.utc)
        search_pub_after = search_pub_before - timedelta(hours=12.0)
        try:
            logger.info(
                "get videos by youtube search",
                extra={"query": query, "published_before": search_pub_before, "published_after": search_pub_after},
            )
            search_videos = youtube_search(
                query=query, published_after=search_pub_after, published_before=search_pub_before, api_key=api_key
            )
            logger.info(
                "got videos by youtube search",
                extra={"videos_count": len(search_videos)},
            )
        except HttpError as e:
            logger.warn(
                "http error by youtube search",
                extra={"status": e.resp.status, "content": e.content},
            )
            return
        except Exception:
            logger.error("unknown exceptions by youtube search", exc_info=True)
            return

        for boss in bosses:
            other_boss_names = [b.name for b in bosses if b.name not in boss.name]
            boss_regex = re.compile(boss.name)
            ignore_boss_regex = re.compile("|".join(other_boss_names))
            ignore_words_regex = re.compile("|".join(IGNORE_WORDS))
            videos = [
                v
                for v in search_videos
                if boss_regex.search(v.title) is not None
                and ignore_boss_regex.search(v.title) is None
                and ignore_words_regex.search(v.title) is None
                and v.damage > 0
            ]

            gotten_pub_after = search_pub_before - timedelta(days=10.0)
            gotten_videos = mongo.TLVideoGotten.Gets(published_after=gotten_pub_after, boss_number=boss.number)
            gotten_vids = [g.video_id for g in gotten_videos]
            gotten_vids = gotten_vids if gotten_vids is not None else []
            yet_gotten_videos = [
                mongo.TLVideoGotten(v.vid, v.published_at, boss.number) for v in videos if v.vid not in gotten_vids
            ]
            yet_gotten_videos = yet_gotten_videos if yet_gotten_videos is not None else []
            for yet_gv in yet_gotten_videos:
                yet_gv.Set()
            target_vids = gotten_vids + [v.video_id for v in yet_gotten_videos]
            if not target_vids:
                continue
            try:
                logger.info(
                    "get youtube video",
                    extra={"video_ids_count": len(target_vids), "boss_number": boss.number},
                )
                target_videos_src = get_youtube_videos(target_vids, api_key)
                logger.info(
                    "got youtube video",
                    extra={"video_ids_count": len(target_videos_src), "boss_number": boss.number},
                )
            except HttpError as e:
                logger.warn(
                    "http error by get youtube video",
                    extra={"status": e.resp.status, "content": e.content},
                )
                continue
            except Exception:
                logger.error("unknown exceptions by get youtube video", exc_info=True)
                continue

            for is_carry_over in [False, True]:
                await asyncio.sleep(10)
                target_videos = [
                    v
                    for v in target_videos_src
                    if boss_regex.search(v.title) and bool(re.search(r"(持ち?越|\d\d[s秒])", v.title)) == is_carry_over
                ]
                target_videos.sort(key=lambda x: x.damage, reverse=True)
                updated_at = datetime.now(timezone(timedelta(hours=9)))
                updated_at_str = updated_at.strftime("%Y/%m/%d %H:%M:%S")
                content = f"TL動画対象ボス: {boss.name}"
                if is_carry_over:
                    content += " (持ち越し)"
                content += f"\n最終更新日時: {updated_at_str}\nヒット件数: {len(target_videos)}, ダメージ上位10件を表示"
                embeds = [create_video_embed(v, updated_at) for v in target_videos[:10]]
                self.cached_embeds[f"{boss.number}_{int(is_carry_over)}"] = (content, embeds)

                subsc_msgs = mongo.ListTLSubscMessage.Gets(boss.number, is_carry_over)
                err_msgs: list[mongo.ListTLSubscMessage] = []
                for msg in subsc_msgs:
                    await asyncio.sleep(1)
                    logger.info(
                        "edit subscribe message for tl videos",
                        extra={
                            "boss_number": boss.number,
                            "guild_id": msg.guild_id,
                            "channel_id": msg.channel_id,
                            "message_id": msg.message_id,
                        },
                    )
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
                                "boss_number": boss.number,
                                "guild_id": msg.guild_id,
                                "channel_id": msg.channel_id,
                                "message_id": msg.message_id,
                            },
                        )
                    except Exception:
                        logger.error(
                            "unknown exceptions by edit subscribe message",
                            exc_info=True,
                            extra={
                                "boss_number": boss.number,
                                "guild_id": msg.guild_id,
                                "channel_id": msg.channel_id,
                                "message_id": msg.message_id,
                            },
                        )

                for em in err_msgs:
                    # 編集するメッセージがない(削除された)場合、subsc_msgsから当メッセージを外す
                    logger.info(
                        "remove subscribe message",
                        extra={
                            "boss_number": boss.number,
                            "guild_id": em.guild_id,
                            "channel_id": em.channel_id,
                            "message_id": em.message_id,
                        },
                    )
                    if em.Delete() is False:
                        logger.warn(
                            "failed to remove subscribe message",
                            extra={
                                "boss_number": boss.number,
                                "guild_id": em.guild_id,
                                "channel_id": em.channel_id,
                                "message_id": em.message_id,
                            },
                        )

            target_videos_src.sort(key=lambda x: x.damage, reverse=True)
            yet_list = [(i, v) for i, v in enumerate(target_videos_src) if v.vid not in gotten_vids]
            if len(yet_list) == 0:
                continue
            notice_content = "TL動画対象ボス: {}\n通知時ダメージ順位: [{}]".format(
                boss.name, ", ".join([f"**{str(i + 1)}**" if i <= 2 else str(i + 1) for i, _ in yet_list])
            )
            notice_video_embeds = [create_video_embed(v, updated_at) for _, v in yet_list]
            notify_list = mongo.TLVideoNotify.Gets()
            err_notify_list: list[mongo.TLVideoNotify] = []
            for notify in notify_list:
                await asyncio.sleep(1)
                logger.info(
                    "notify new tl videos",
                    extra={
                        "boss_number": boss.number,
                        "guild_id": notify.guild_id,
                        "channel_id": notify.channel_id,
                    },
                )
                try:
                    guild = self.bot.get_guild(notify.guild_id)
                    if guild is None:
                        guild = await self.bot.fetch_guild(notify.guild_id)
                    channel = guild.get_channel(notify.channel_id)
                    if channel is None:
                        channel = await guild.fetch_channel(notify.channel_id)
                    await channel.send(content=notice_content, embeds=notice_video_embeds[:10])
                except discord.NotFound:
                    err_notify_list.append(notify)
                except HTTPException:
                    logger.error(
                        "HTTP exception by notify new tl video",
                        exc_info=True,
                        extra={
                            "boss_number": boss.number,
                            "guild_id": notify.guild_id,
                            "channel_id": notify.channel_id,
                        },
                    )
                except Exception:
                    logger.error(
                        "unknown exceptions by notify new tl video",
                        exc_info=True,
                        extra={
                            "boss_number": boss.number,
                            "guild_id": notify.guild_id,
                            "channel_id": notify.channel_id,
                        },
                    )

            for err_notify in err_notify_list:
                # チャンネルがない(削除された)場合、ti_video_notifyから当チャンネルを外す
                logger.info(
                    "remove tl video notify",
                    extra={
                        "boss_number": boss.number,
                        "guild_id": err_notify.guild_id,
                        "channel_id": err_notify.channel_id,
                    },
                )
                err_notify.Delete()

    @slash_command(guild_ids=config.guild_ids, name="list_tl", description="定期的なTL動画のリストアップ(30分毎に更新)")
    @cmd_log.info("call list tl videos command")
    async def ListTLVideosCommand(
        self,
        ctx: discord.ApplicationContext,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
        is_carry_over: Option(bool, is_carry_over_desc),
    ):
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

        boss = mongo.BossInfo.Get(number=boss_num)
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

        if self.cached_embeds[f"{boss.number}_{int(is_carry_over)}"] == ():
            content = f"TL動画対象ボス: {boss.name}"
            if is_carry_over:
                content += " (持ち越し)"
            content += "\n次の定期更新までお待ちください。"
            interact: discord.Interaction = await ctx.respond(content)
            msg = await interact.original_message()
            mongo.ListTLSubscMessage(msg.guild.id, msg.channel.id, msg.id, boss.number, is_carry_over).Set()
        else:
            content, embeds = self.cached_embeds[f"{boss.number}_{int(is_carry_over)}"]
            interact: discord.Interaction = await ctx.respond(content, embeds=embeds)
            msg = await interact.original_message()
            mongo.ListTLSubscMessage(msg.guild.id, msg.channel.id, msg.id, boss.number, is_carry_over).Set()

    @ListTLVideosCommand.error
    @cmd_log.error("list tl videos command error")
    async def ListTLVideosCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="list_tl_notify_register", description="TL動画の新着通知を登録")
    @cmd_log.info("call list tl videos notify register command")
    async def ListTLVideosNotifyRegisterCommand(self, ctx: discord.ApplicationContext):
        notify_list = mongo.TLVideoNotify.Gets()
        notify = next(
            filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, notify_list), None
        )
        if notify is None:
            mongo.TLVideoNotify(guild_id=ctx.guild_id, channel_id=ctx.channel_id).Set()
            return await ctx.respond("通知登録しました。")
        else:
            return await ctx.respond("既に登録されています。", ephemeral=True)

    @ListTLVideosNotifyRegisterCommand.error
    async def ListTLVideosNotifyRegisterCommand_error(self, ctx: discord.ApplicationContext, error):
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message

    @slash_command(guild_ids=config.guild_ids, name="list_tl_notify_unregister", description="TL動画の新着通知を登録")
    @cmd_log.info("call list tl videos notify unregister command")
    async def ListTLVideosNotifyUnregisterCommand(self, ctx: discord.ApplicationContext):
        notify_list = mongo.TLVideoNotify.Gets()
        notyfy = next(
            filter(lambda x: x.guild_id == ctx.guild.id and x.channel_id == ctx.channel.id, notify_list), None
        )
        if notyfy is not None:
            notyfy.Delete()
            return await ctx.respond("通知登録を解除しました。")
        else:
            return await ctx.respond("登録されていません。", ephemeral=True)

    @ListTLVideosNotifyUnregisterCommand.error
    @cmd_log.error("list tl videos notify unregister command error")
    async def ListTLVideosNotifyUnregisterCommand_error(self, ctx: discord.ApplicationContext, error):
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
        self.title: str = youtube_item["snippet"]["title"]
        self.vid: str = youtube_item["id"]["videoId"] if type(youtube_item["id"]) is dict else youtube_item["id"]
        self.published_at = datetime.fromisoformat(youtube_item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        self.damage = self.__get_damage()

    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.vid}"

    def __get_damage(self) -> int:
        ext_dmgs = re.findall(r"\d{0,2},?\d{3,}(?![年s/])", self.title)
        ignore_dmg = str(self.published_at.year)
        if ignore_dmg in ext_dmgs:
            ext_dmgs.remove(ignore_dmg)
        if len(ext_dmgs) > 0:
            return max([int(re.sub("[,]", "", d)) for d in ext_dmgs])
        else:
            return -1


class TLVideoDetail(TLVideo):
    def __init__(self, youtube_item) -> None:
        super().__init__(youtube_item)
        self.description: str = youtube_item["snippet"]["description"]
        self.channel_title: str = youtube_item["snippet"]["channelTitle"]
        self.thumbnail_url: str = youtube_item["snippet"]["thumbnails"]["medium"]["url"]
        self.party = self.__get_party()

    def __get_party(self) -> str:
        desc_lines = self.description.splitlines()
        party_index = -1
        party_regex = re.compile("パーティ編成")
        for i, line in enumerate(desc_lines):
            if party_regex.search(line) is not None:
                party_index = i + 1
                break
        if party_index > 0 and len(desc_lines) - party_index >= 5:
            party_members = [line for line in desc_lines[party_index : party_index + 5]]
            return "\n".join(party_members)

        party_members = [line for line in desc_lines if re.search(r"[★☆星]\d(\s|　)*(Lv|lv|最強)", line)]
        if len(party_members) >= 5:
            return "\n".join(party_members[:5])

        party_members_candidate = set(self.description.split())
        party_members_candidate = [candi.replace("（", "(").replace("）", ")") for candi in party_members_candidate]
        party_members = [candi for candi in party_members_candidate if char.is_play_char(candi)]
        if len(party_members) >= 1:
            party_members.extend(["???"] * (5 - len(party_members)))
            return "\n".join(party_members[:5])
        else:
            return "編成の取得に失敗しました"


def create_video_embed(video: TLVideoDetail, updated_at: datetime) -> discord.Embed:
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
    embed.add_field(name="パーティ編成", value=video.party)
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


def youtube_search(
    query: str, published_after: datetime, published_before: datetime, api_key: str, page_token: Optional[str] = None
) -> list[TLVideo]:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    response = (
        youtube.search()
        .list(
            q=query,
            part="id,snippet",
            publishedAfter=published_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
            publishedBefore=published_before.strftime("%Y-%m-%dT%H:%M:%SZ"),
            order="relevance",
            type="video",
            maxResults=50,
            pageToken=page_token,
        )
        .execute()
    )

    videos = [TLVideo(result) for result in response.get("items", []) if result["id"]["kind"] == "youtube#video"]

    next_page_token = response.get("nextPageToken")
    if next_page_token:
        next_videos = youtube_search(
            query=query,
            published_after=published_after,
            published_before=published_before,
            api_key=api_key,
            page_token=next_page_token,
        )
        videos += next_videos

    return videos


def get_youtube_videos(vid_list: list[str], api_key: str, page_token: Optional[str] = None) -> list[TLVideoDetail]:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)
    response = (
        youtube.videos()
        .list(
            part="id,snippet",
            id=",".join(vid_list),
            maxResults=50,
            pageToken=page_token,
        )
        .execute()
    )

    videos = [TLVideoDetail(result) for result in response.get("items", []) if result["kind"] == "youtube#video"]

    next_page_token = response.get("nextPageToken")
    if next_page_token:
        next_videos = get_youtube_videos(
            vid_list=vid_list,
            api_key=api_key,
            page_token=next_page_token,
        )
        videos += next_videos

    return videos
