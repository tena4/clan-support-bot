from __future__ import annotations

from logging import getLogger
from typing import Iterable, Optional

import pymongo

import app_config

logger = getLogger(__name__)
config = app_config.Config.get_instance()


class MongoConn:
    __db = None
    __db_name = "clan_support"

    @classmethod
    def get_db(cls):
        if cls.__db is None:
            logger.info("mongodb connection")
            cls.__db = pymongo.MongoClient(config.database_url)[cls.__db_name]
        return cls.__db

    @classmethod
    def close_conn(cls):
        if cls.__db is not None:
            cls.__db.client.close()


def get_one(clt_name: str, filter: dict) -> Optional[dict]:
    db = MongoConn.get_db()
    collection = db[clt_name]
    doc = collection.find_one(filter=filter)
    return doc


def get_many(clt_name: str, filter: Optional[dict] = None) -> Iterable[dict]:
    db = MongoConn.get_db()
    collection = db[clt_name]
    docs = collection.find(filter=filter)
    for doc in docs:
        yield doc


def upsert_one(clt_name: str, filter: dict, update: dict) -> bool:
    db = MongoConn.get_db()
    collection = db[clt_name]
    result = collection.update_one(filter=filter, update=update, upsert=True)
    return result.matched_count > 0


def insert_many(clt_name: str, docs: Iterable[dict]) -> bool:
    db = MongoConn.get_db()
    collection = db[clt_name]
    result = collection.insert_many(documents=docs)
    return len(result.inserted_ids) > 0


def delete_one(clt_name: str, filter: dict) -> bool:
    db = MongoConn.get_db()
    collection = db[clt_name]
    result = collection.delete_one(filter=filter)
    return result.deleted_count > 0
