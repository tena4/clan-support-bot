from datetime import datetime, timezone, timedelta
from http.client import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import discord
from discord.commands import slash_command, Option
from discord.ext import tasks, commands
from discord.ext.commands.context import Context
import app_config
from main import BotClass
import re
import postgres_helper as pg

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

config = app_config.Config.get_instance()


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
        self.bot.logger.info("run scheduled tl search")
        bosses = pg.get_bosses_info()
        for boss in bosses:
            query = f"{boss.name}+5段階目+万"
            api_key = self.get_api_key()
            try:
                self.bot.logger.debug(f'youtube search. query: "{query}"')
                videos = youtube_search(query, api_key)
            except HttpError as e:
                self.bot.logger.warn("An HTTP error %d occurred:\n%s", e.resp.status, e.content)
                break

            other_boss_names = [b.name for b in bosses if b != boss]
            boss_regex = re.compile(boss.name)
            ignore_boss_regex = re.compile("|".join(other_boss_names))
            videos = [
                v
                for v in videos
                if boss_regex.search(v.title) is not None
                and ignore_boss_regex.search(v.title) is None
                and v.damage > 0
            ]

            videos.sort(key=lambda x: x.damage, reverse=True)
            updated_at = datetime.now(timezone(timedelta(hours=9)))
            updated_at_str = updated_at.strftime("%Y/%m/%d %H:%M:%S")
            content = f"TL動画対象ボス: {boss.name}\r\n最終更新日時: {updated_at_str}\r\nヒット件数: {len(videos)}, ダメージ上位10件を表示"

            embeds = [create_video_embed(v, updated_at) for v in videos[:10]]
            self.cached_embeds[boss.number] = (content, embeds)

            subsc_msgs = pg.get_subsc_messages(boss.number)
            err_msgs = []
            for msg in subsc_msgs:
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
                    # 編集するメッセージがない(削除された)場合、subsc_msgsから当メッセージを外す
                    self.bot.logger.info("remove message subscriber. message.id: %s", msg.message_id)
                    err_msgs.append(msg)
                except HTTPException as e:
                    self.bot.logger.error("error edit subscribe message. message.id: %s. error: %s", msg.message_id, e)

            for em in err_msgs:
                pg.delete_subsc_message(em.guild_id, em.channel_id, em.message_id)

    @slash_command(guild_ids=config.guild_ids, name="list_tl", description="定期的なTL動画のリストアップ(30分毎に更新)")
    async def ListTLVideosCommand(
        self,
        ctx: Context,
        boss_num: Option(int, boss_num_desc, choices=[1, 2, 3, 4, 5]),
    ):
        self.bot.logger.info("call list tl videos command. author.id: %s", ctx.author.id)
        if not self.enabled:
            await ctx.respond("環境変数の設定が正しくされていません。(YOUTUBE_API_KEY)", ephemeral=True)
            return

        boss = pg.get_boss_info(boss_num)
        if boss is None:
            await ctx.respond(f"{boss_num}ボスの情報が登録されていません。", ephemeral=True)
            return

        if self.cached_embeds[boss.number] == ():
            content = f"TL動画リスト: {boss.name}\r\n次の定期更新までお待ちください。"
            interact: discord.Interaction = await ctx.respond(content)
            msg = await interact.original_message()
            pg.set_subsc_message(msg.guild.id, msg.channel.id, msg.id, boss.number)
        else:
            content, embeds = self.cached_embeds[boss.number]
            interact: discord.Interaction = await ctx.respond(content, embeds=embeds)
            msg = await interact.original_message()
            pg.set_subsc_message(msg.guild.id, msg.channel.id, msg.id, boss.number)

    @ListTLVideosCommand.error
    async def ListTLVideosCommand_error(self, ctx: Context, error):
        self.bot.logger.error("list tl videos command error: {%s}", error)
        return await ctx.respond(error, ephemeral=True)  # ephemeral makes "Only you can see this" message


def setup(bot):
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
        self.description = youtube_item["snippet"]["description"]
        self.channel_title = youtube_item["snippet"]["channelTitle"]
        self.published_at = datetime.fromisoformat(youtube_item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        self.thumbnail_url = youtube_item["snippet"]["thumbnails"]["default"]["url"]
        self.damage = self.__get_damage()

    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.vid}"

    def __get_damage(self):
        ext_dmgs = re.findall(r"\d[,\d]+万", self.title)
        if len(ext_dmgs) > 0:
            return max([int(re.sub("[,万]", "", d)) for d in ext_dmgs])
        else:
            return -1


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


def youtube_search(query: str, api_key: str) -> list[TLVideo]:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)
    published_after = datetime.now() - timedelta(days=14.0)

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
            maxResults=30,
        )
        .execute()
    )

    videos = [
        TLVideo(result) for result in search_response.get("items", []) if result["id"]["kind"] == "youtube#video"
    ]

    return videos
