from __future__ import annotations

from datetime import date, datetime
from logging import getLogger
from typing import Optional

import app_config
import mongo_helper as helper

logger = getLogger(__name__)
config = app_config.Config.get_instance()


class BossInfo:
    __clt_name = "boss_info"

    def __init__(self, number: int, name: str, hp: int, _id: Optional[str] = None) -> None:
        self.number = number
        self.name = name
        self.hp = hp

    @classmethod
    def Get(cls, number: int) -> Optional[BossInfo]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"number": number},
        )
        if doc is None:
            return None
        return BossInfo(**doc)

    @classmethod
    def Gets(cls) -> list[BossInfo]:
        docs = helper.get_many(cls.__clt_name)
        return [BossInfo(**doc) for doc in docs]

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"number": self.number},
            update={
                "$set": {"name": self.name, "hp": self.hp},
            },
        )


class ListTLSubscMessage:
    __clt_name = "list_tl_subscribe"

    def __init__(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        boss_number: int,
        is_carry_over: bool,
        _id: Optional[str] = None,
    ) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        self.boss_number = boss_number
        self.is_carry_over = is_carry_over

    @classmethod
    def Gets(cls, boss_number: int, is_carry_over: bool) -> list[ListTLSubscMessage]:
        docs = helper.get_many(
            cls.__clt_name,
            filter={"$and": [{"boss_number": boss_number}, {"is_carry_over": is_carry_over}]},
        )
        return [ListTLSubscMessage(**doc) for doc in docs]

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={
                "$and": [
                    {"guild_id": self.guild_id},
                    {"boss_number": self.boss_number},
                    {"is_carry_over": self.is_carry_over},
                ]
            },
            update={"$set": {"channel_id": self.channel_id, "message_id": self.message_id}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={
                "$and": [
                    {"guild_id": self.guild_id},
                    {"channel_id": self.channel_id},
                    {"message_id": self.message_id},
                ]
            },
        )
        return is_deleted


class AttackReportRegister:
    __clt_name = "attack_report_register"

    def __init__(
        self, guild_id: int, channel_id: int, last_published: date | datetime, _id: Optional[str] = None
    ) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.last_published = date(last_published.year, last_published.month, last_published.day)

    @classmethod
    def Gets(cls) -> list[AttackReportRegister]:
        docs = helper.get_many(cls.__clt_name)
        return [AttackReportRegister(**doc) for doc in docs]

    def Set(self) -> None:
        last_pub_dt = datetime(self.last_published.year, self.last_published.month, self.last_published.day)
        helper.upsert_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"channel_id": self.channel_id}]},
            update={"$set": {"last_published": last_pub_dt}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"channel_id": self.channel_id}]},
        )
        return is_deleted


class ClanBattleSchedule:
    __clt_name = "clan_battle_schedule"

    def __init__(
        self,
        start_date: date | datetime,
        end_date: date | datetime,
        id: Optional[int] = None,
        _id: Optional[str] = None,
    ) -> None:
        self.start_date = date(start_date.year, start_date.month, start_date.day)
        self.end_date = date(end_date.year, end_date.month, end_date.day)

    @classmethod
    def Get(cls) -> Optional[ClanBattleSchedule]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"id": 1},
        )
        if doc is None:
            return None
        return ClanBattleSchedule(**doc)

    def Set(self) -> None:
        start_datetime = datetime(self.start_date.year, self.start_date.month, self.start_date.day)
        end_datetime = datetime(self.end_date.year, self.end_date.month, self.end_date.day)
        helper.upsert_one(
            self.__clt_name,
            filter={"id": 1},
            update={"$set": {"start_date": start_datetime, "end_date": end_datetime}},
        )


class TLVideoNotify:
    __clt_name = "tl_video_notify"

    def __init__(self, guild_id: int, channel_id: str, _id: Optional[str] = None) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id

    @classmethod
    def Gets(cls) -> list[TLVideoNotify]:
        docs = helper.get_many(cls.__clt_name)
        return [TLVideoNotify(**doc) for doc in docs]

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
            update={"$set": {"channel_id": self.channel_id}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
        )
        return is_deleted


class TLVideoGotten:
    __clt_name = "tl_video_gotten"

    def __init__(self, video_id: str, published_at: datetime, boss_number: int, _id: Optional[str] = None) -> None:
        self.video_id = video_id
        self.published_at = published_at
        self.boss_number = boss_number

    @classmethod
    def Gets(cls, published_after: datetime, boss_number: int) -> list[TLVideoGotten]:
        docs = helper.get_many(
            cls.__clt_name,
            filter={"$and": [{"published_at": {"$gt": published_after}}, {"boss_number": boss_number}]},
        )
        return [TLVideoGotten(**doc) for doc in docs]

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"video_id": self.video_id},
            update={"$set": {"published_at": self.published_at, "boss_number": self.boss_number}},
        )


class ClanMemberRole:
    __clt_name = "clan_member_role"

    def __init__(self, guild_id: int, role_id: int, _id: Optional[str] = None) -> None:
        self.guild_id = guild_id
        self.role_id = role_id

    @classmethod
    def Get(cls, guild_id: int) -> Optional[ClanMemberRole]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"guild_id": guild_id},
        )
        if doc is None:
            return None
        return ClanMemberRole(**doc)

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
            update={"$set": {"role_id": self.role_id}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
        )
        return is_deleted


class ConcurrentAttackNotify:
    __clt_name = "concurrent_attack_notify"

    def __init__(self, guild_id: int, channel_id: int, level: int, _id: Optional[str] = None) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.level = level

    @classmethod
    def Get(cls, guild_id: int) -> Optional[ConcurrentAttackNotify]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"guild_id": guild_id},
        )
        if doc is None:
            return None
        return ConcurrentAttackNotify(**doc)

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
            update={"$set": {"channel_id": self.channel_id, "level": self.level}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"guild_id": self.guild_id},
        )
        return is_deleted


class TemplateUnfreezeMessage:
    __clt_name = "template_unfreeze_message"

    def __init__(
        self, guild_id: int, boss_number: int, template: str, image_url: str, _id: Optional[str] = None
    ) -> None:
        self.guild_id = guild_id
        self.boss_number = boss_number
        self.template = template
        self.image_url = image_url

    @classmethod
    def Get(cls, guild_id: int, boss_number: int) -> Optional[TemplateUnfreezeMessage]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"$and": [{"guild_id": guild_id}, {"boss_number": boss_number}]},
        )
        if doc is None:
            return None
        return TemplateUnfreezeMessage(**doc)

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"boss_number": self.boss_number}]},
            update={"$set": {"template": self.template, "image_url": self.image_url}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"boss_number": self.boss_number}]},
        )
        return is_deleted


class TemplateAttackStartMessage:
    __clt_name = "template_attack_start_message"

    def __init__(
        self, guild_id: int, boss_number: int, template: str, image_url: str, _id: Optional[str] = None
    ) -> None:
        self.guild_id = guild_id
        self.boss_number = boss_number
        self.template = template
        self.image_url = image_url

    @classmethod
    def Get(cls, guild_id: int, boss_number: int) -> Optional[TemplateAttackStartMessage]:
        doc = helper.get_one(
            cls.__clt_name,
            filter={"$and": [{"guild_id": guild_id}, {"boss_number": boss_number}]},
        )
        if doc is None:
            return None
        return TemplateAttackStartMessage(**doc)

    def Set(self) -> None:
        helper.upsert_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"boss_number": self.boss_number}]},
            update={"$set": {"template": self.template, "image_url": self.image_url}},
        )

    def Delete(self) -> bool:
        is_deleted = helper.delete_one(
            self.__clt_name,
            filter={"$and": [{"guild_id": self.guild_id}, {"boss_number": self.boss_number}]},
        )
        return is_deleted
