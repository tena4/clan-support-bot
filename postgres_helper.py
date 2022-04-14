from collections import namedtuple
import psycopg2
import app_config
from datetime import date

config = app_config.Config.get_instance()
BossInfo = namedtuple("BossInfo", ("number", "name", "hp"))
SubscMessage = namedtuple("SubscMessage", ("guild_id", "channel_id", "message_id", "boss_number"))
AttacReportRegister = namedtuple("AttacReportRegister", ("guild_id", "channel_id", "last_published"))
ClanBattleSchedule = namedtuple("ClanBattleSchedule", ("start_date", "end_date"))


def get_connection():
    dsn = config.database_url
    conn = psycopg2.connect(dsn, sslmode="require")
    conn.autocommit = True
    return conn


def db_init():
    with get_connection() as conn:
        __create_boss_info_table(conn)
        __create_list_tl_subscribe(conn)
        __create_attack_report_register(conn)
        __create_clan_battle_schedule(conn)


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
                "(guild_id bigint, channel_id bigint, message_id bigint, boss_number integer);"
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


def get_boss_info(number: int) -> BossInfo:
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


def get_subsc_messages(boss_num: int) -> list[SubscMessage]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "SELECT guild_id, channel_id, message_id, boss_number "
                    "FROM list_tl_subscribe "
                    "WHERE boss_number = %s;"
                ),
                (boss_num,),
            )
            records = cur.fetchall()
            subsc_msgs = [SubscMessage(g, c, m, b) for g, c, m, b in records]
            return subsc_msgs


def set_subsc_message(guild_id: int, channel_id: int, message_id: int, boss_number: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO list_tl_subscribe (guild_id, channel_id, message_id, boss_number) "
                    "VALUES (%s, %s, %s, %s);"
                ),
                (guild_id, channel_id, message_id, boss_number),
            )


def delete_subsc_message(guild_id: int, channel_id: int, message_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM list_tl_subscribe WHERE guild_id = %s AND channel_id = %s AND message_id = %s;",
                (guild_id, channel_id, message_id),
            )


def get_attack_report_register_list() -> list[AttacReportRegister]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT guild_id, channel_id, last_published FROM attack_report_register;")
            records = cur.fetchall()
            reglist = [AttacReportRegister(record[0], record[1], record[2]) for record in records]
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


def get_clan_battle_schedule() -> ClanBattleSchedule:
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
