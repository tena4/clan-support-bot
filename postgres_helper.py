from collections import namedtuple
from datetime import date, datetime
from logging import getLogger
from typing import Optional

import psycopg2
from psycopg2 import extras

import app_config

logger = getLogger(__name__)
config = app_config.Config.get_instance()

BossInfo = namedtuple("BossInfo", ("number", "name", "hp"))
SubscMessage = namedtuple("SubscMessage", ("guild_id", "channel_id", "message_id", "boss_number", "is_carry_over"))
AttackReportRegister = namedtuple("AttackReportRegister", ("guild_id", "channel_id", "last_published"))
ClanBattleSchedule = namedtuple("ClanBattleSchedule", ("start_date", "end_date"))
TLVideoNotify = namedtuple("TLVideoNotify", ("guild_id", "channel_id"))
TLVideoGotten = namedtuple("TLVideoGotten", ("video_id", "published_at", "boss_number"))
ClanMemberRole = namedtuple("ClanMemberRole", ("guild_id", "role_id"))
ConcurrentAttackNotify = namedtuple("ConcurrentAttackNotify", ("guild_id", "channel_id", "level"))


def get_connection():
    try:
        dsn = config.database_url
        conn = psycopg2.connect(dsn, sslmode="require")
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error("Postgresql connection error", exc_info=True)
        raise e


def db_init():
    with get_connection() as conn:
        __create_boss_info_table(conn)
        __create_list_tl_subscribe(conn)
        __create_attack_report_register(conn)
        __create_clan_battle_schedule(conn)
        __create_tl_video_notify(conn)
        __create_tl_video_gotten(conn)
        __create_clan_member_role(conn)
        __create_concurrent_attack_notify(conn)


def __create_boss_info_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            ("CREATE TABLE IF NOT EXISTS boss_info (number integer PRIMARY KEY, name varchar(64), hp integer);")
        )


def __create_list_tl_subscribe(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS list_tl_subscribe"
                "(guild_id bigint, channel_id bigint, message_id bigint, boss_number integer, is_carry_over boolean);"
            )
        )


def __create_attack_report_register(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS attack_report_register"
                "(id varchar(64) PRIMARY KEY, guild_id bigint, channel_id bigint, last_published date);"
            )
        )


def __create_clan_battle_schedule(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS clan_battle_schedule"
                "(id integer PRIMARY KEY, start_date date, end_date date);"
            )
        )


def __create_tl_video_notify(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS tl_video_notify"
                "(guild_id bigint, channel_id bigint, PRIMARY KEY (guild_id, channel_id));"
            )
        )


def __create_tl_video_gotten(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS tl_video_gotten"
                "(video_id varchar(32) PRIMARY KEY, published_at timestamp, boss_number integer);"
            )
        )


def __create_clan_member_role(conn):
    with conn.cursor() as cur:
        cur.execute(("CREATE TABLE IF NOT EXISTS clan_member_role" "(guild_id bigint PRIMARY KEY, role_id bigint);"))


def __create_concurrent_attack_notify(conn):
    with conn.cursor() as cur:
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS concurrent_attack_notify"
                "(guild_id bigint PRIMARY KEY, channel_id bigint, level integer);"
            )
        )


def get_boss_info(number: int) -> Optional[BossInfo]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT number, name, hp FROM boss_info WHERE number = %s;", (number,))
            record = cur.fetchone()
            if record is None:
                return None
            boss = BossInfo(record[0], record[1], record[2])
            return boss


def get_bosses_info() -> list[BossInfo]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT number, name, hp FROM boss_info ORDER BY number ASC;")
            records = cur.fetchall()
            bosses = [BossInfo(num, name, hp) for num, name, hp in records]
            return bosses


def set_boss_info(boss_number: int, name: str, hp: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO boss_info (number, name, hp) values (%s, %s, %s) "
                    "ON CONFLICT (number) "
                    "DO UPDATE SET name = %s, hp = %s;"
                ),
                (boss_number, name, hp, name, hp),
            )


def get_subsc_messages(boss_num: int, is_carry_over: bool) -> list[SubscMessage]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "SELECT guild_id, channel_id, message_id, boss_number, is_carry_over "
                    "FROM list_tl_subscribe "
                    "WHERE boss_number = %s AND is_carry_over = %s;"
                ),
                (boss_num, is_carry_over),
            )
            records = cur.fetchall()
            subsc_msgs = [SubscMessage(g, c, m, b, co) for g, c, m, b, co in records]
            return subsc_msgs


def set_subsc_message(guild_id: int, channel_id: int, message_id: int, boss_number: int, is_carry_over: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO list_tl_subscribe (guild_id, channel_id, message_id, boss_number, is_carry_over) "
                    "VALUES (%s, %s, %s, %s, %s);"
                ),
                (guild_id, channel_id, message_id, boss_number, is_carry_over),
            )


def delete_subsc_message(guild_id: int, channel_id: int, message_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM list_tl_subscribe WHERE guild_id = %s AND channel_id = %s AND message_id = %s;",
                (guild_id, channel_id, message_id),
            )


def get_attack_report_register_list() -> list[AttackReportRegister]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT guild_id, channel_id, last_published FROM attack_report_register;")
            records = cur.fetchall()
            reglist = [AttackReportRegister(record[0], record[1], record[2]) for record in records]
            return reglist


def set_attack_report_register(guild_id: int, channel_id: int, last_date: date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            last_ds = last_date.strftime("%Y-%m-%d")
            cur.execute(
                (
                    "INSERT INTO attack_report_register (id, guild_id, channel_id, last_published)"
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (id) "
                    "DO NOTHING;"
                ),
                (f"{guild_id}_{channel_id}", guild_id, channel_id, last_ds),
            )


def remove_attack_report_register(guild_id: int, channel_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                ("DELETE FROM attack_report_register WHERE guild_id = %s AND channel_id = %s;"),
                (guild_id, channel_id),
            )


def get_clan_battle_schedule() -> Optional[ClanBattleSchedule]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT start_date, end_date FROM clan_battle_schedule WHERE id = 1;")
            record = cur.fetchone()
            if record is None:
                return None
            cbs = ClanBattleSchedule(record[0], record[1])
            return cbs


def set_clan_battle_schedule(start_date: date, end_date: date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            start_ds = start_date.strftime("%Y-%m-%d")
            end_ds = end_date.strftime("%Y-%m-%d")
            cur.execute(
                (
                    "INSERT INTO clan_battle_schedule (id, start_date, end_date) VALUES (1, %s, %s) "
                    "ON CONFLICT (id) "
                    "DO UPDATE SET start_date = %s, end_date = %s;"
                ),
                (start_ds, end_ds, start_ds, end_ds),
            )


def get_tl_video_notify_list() -> list[TLVideoNotify]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT guild_id, channel_id FROM tl_video_notify;")
            records = cur.fetchall()
            notify_list = [TLVideoNotify(record[0], record[1]) for record in records]
            return notify_list


def set_tl_video_notify(guild_id: int, channel_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                ("INSERT INTO tl_video_notify (guild_id, channel_id)" "VALUES (%s, %s) "),
                (guild_id, channel_id),
            )


def remove_tl_video_notify(guild_id: int, channel_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                ("DELETE FROM tl_video_notify WHERE guild_id = %s AND channel_id = %s;"),
                (guild_id, channel_id),
            )


def get_tl_video_gotten_list(published_after: datetime, boss_number: int) -> list[TLVideoGotten]:
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                (
                    "SELECT video_id, published_at, boss_number FROM tl_video_gotten "
                    "WHERE published_at > %s AND boss_number = %s;"
                ),
                (published_after.strftime("%Y-%m-%d %H:%M:%S"), boss_number),
            )
            records = cur.fetchall()
            gotten_list = [TLVideoGotten(record[0], record[1], record[2]) for record in records]
            return gotten_list


def set_tl_video_gotten_list(videos: list[TLVideoGotten]):
    with get_connection() as conn:
        with conn.cursor() as cur:
            extras.execute_values(
                cur,
                (
                    "INSERT INTO tl_video_gotten (video_id, published_at, boss_number) VALUES %s "
                    "ON CONFLICT (video_id) "
                    "DO NOTHING;"
                ),
                (videos),
            )


def get_clan_member_role(guild_id: int) -> Optional[ClanMemberRole]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT guild_id, role_id FROM clan_member_role WHERE guild_id = %s;",
                (guild_id,),
            )
            record = cur.fetchone()
            if record is None:
                return None
            return ClanMemberRole(record[0], record[1])


def set_clan_member_role(guild_id: int, role_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO clan_member_role (guild_id, role_id)"
                    "VALUES (%s, %s) "
                    "ON CONFLICT (guild_id) "
                    "DO UPDATE SET role_id = %s;"
                ),
                (guild_id, role_id, role_id),
            )


def remove_clan_member_role(guild_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM clan_member_role WHERE guild_id = %s;",
                (guild_id,),
            )


def get_concurrent_attack_notify(guild_id: int) -> Optional[ConcurrentAttackNotify]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT guild_id, channel_id, level FROM concurrent_attack_notify WHERE guild_id = %s;",
                (guild_id,),
            )
            record = cur.fetchone()
            if record is None:
                return None
            return ConcurrentAttackNotify(record[0], record[1], record[2])


def set_concurrent_attack_notify(guild_id: int, channel_id: int, level: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO concurrent_attack_notify (guild_id, channel_id, level)"
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (guild_id) "
                    "DO UPDATE SET channel_id = %s, level = %s;"
                ),
                (guild_id, channel_id, level, channel_id, level),
            )


def remove_concurrent_attack_notify(guild_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM concurrent_attack_notify WHERE guild_id = %s;",
                (guild_id,),
            )
