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

config = app_config.Config()


class TLVideoCog(commands.Cog):
    boss_num_desc = "ボスの番号"

    def __init__(self, bot: BotClass):
        self.bot = bot
        self.task_count = 0
        self.msg = None
        self.enabled = config.youtube_api_key != ""
        if self.enabled:
            self.cached_embeds: dict[int, (str, list[discord.Embed])] = {i: () for i in range(1, 6)}
            self.scheduled_tl_search.start()

    def cog_unload(self):
        self.scheduled_tl_search.cancel()

    @tasks.loop(hours=2.0)
    async def scheduled_tl_search(self):
        self.bot.logger.info("run scheduled tl search")
        bosses = pg.get_bosses_info()
        for boss in bosses:
            query = f"{boss.name}+5段階目+万"
            try:
                self.bot.logger.debug(f'youtube search. query: "{query}"')
                videos = youtube_search(query)
            except HttpError as e:
                self.bot.logger.warn("An HTTP error %d occurred:\n%s", e.resp.status, e.content)
                break

            videos = [v for v in videos if re.search(boss.name, v.title) is not None and v.damage > 0]
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
                    guild = await self.bot.fetch_guild(msg.guild_id)
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

    @slash_command(guild_ids=config.guild_ids, name="list_tl", description="定期的なTL動画のリストアップ(2時間毎に更新)")
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
    elif delta.seconds >= 0:
        return discord.Colour.red()
    else:
        return discord.Colour.dark_purple()


class TLVideo:
    def __init__(self, youtube_item) -> None:
        self.title = youtube_item["snippet"]["title"]
        self.vid = youtube_item["id"]["videoId"]
        self.published_at = datetime.fromisoformat(youtube_item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        self.thumbnail_url = youtube_item["snippet"]["thumbnails"]["default"]["url"]
        self.damage = self.__get_damage()

    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.vid}"

    def __get_damage(self):
        ext_dmgs = re.findall(r"\d+万", self.title)
        if len(ext_dmgs) > 0:
            return max([int(d.rstrip("万")) for d in ext_dmgs])
        else:
            return -1


def create_video_embed(video: TLVideo, updated_at: datetime) -> discord.Embed:
    pub_at_jp = video.published_at.astimezone(timezone(timedelta(hours=9)))
    pub_at_jp_str = pub_at_jp.strftime("%Y/%m/%d %H:%M:%S")
    embed = discord.Embed(title=video.title, color=timedelta_color(updated_at - pub_at_jp))
    embed.add_field(name="ダメージ", value=f"{video.damage}万")
    embed.add_field(name="URL", value=video.url())
    embed.add_field(name="投稿日時", value=f"{pub_at_jp_str}")
    embed.set_thumbnail(url=video.thumbnail_url)
    return embed


def youtube_search(query: str) -> list[TLVideo]:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=config.youtube_api_key)
    published_after = datetime.now() - timedelta(days=14.0)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = (
        youtube.search()
        .list(
            q=query,
            part="id,snippet",
            publishedAfter=published_after.isoformat() + "Z",
            order="relevance",
            maxResults=30,
        )
        .execute()
    )

    videos = [
        TLVideo(result) for result in search_response.get("items", []) if result["id"]["kind"] == "youtube#video"
    ]

    return videos
