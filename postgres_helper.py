from collections import namedtuple
import psycopg2
import app_config

config = app_config.Config.get_instance()
BossInfo = namedtuple("BossInfo", ("number", "name", "hp"))
SubscMessage = namedtuple("SubscMessage", ("guild_id", "channel_id", "message_id", "boss_number"))


def get_connection():
    dsn = config.database_url
    conn = psycopg2.connect(dsn, sslmode="require")
    conn.autocommit = True
    return conn


def db_init():
    with get_connection() as conn:
        __create_boss_info_table(conn)
        __create_list_tl_subscribe(conn)


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
