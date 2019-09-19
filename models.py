from atom.api import Atom, ContainerList, Unicode, Int, Enum, Bool, Typed, observe, ForwardInstance, List, Instance

from atomdb.sql import SQLModel, SQLModelManager, Relation
from aiopg.sa import create_engine
import sqlalchemy as sa

import asyncio
import os

from datetime import datetime

if "POSTGRES_URL" not in os.environ:
    os.environ["POSTGRES_URL"] = "postgresql://youpsla@localhost:5433/deviant"
DATABASE_URL = os.environ["POSTGRES_URL"]

class User(SQLModel):
    id = Typed(int).tag(type=sa.BigInteger(), primary_key=True)
    name = Unicode()
    screen_name = Unicode()
    followers_count = Int(0)
    statuses_count = Int(0)
    follower = Bool(False)
    tweets = Relation(lambda: Tweet)

    class Meta:
        db_table = 'user'


class Tweet(SQLModel):

    id = Typed(int).tag(type=sa.BigInteger(), primary_key=True)
    text = Unicode()
    retweet = Bool(False)
    created_at = Instance(datetime)
    user = Instance(User).tag(nullable=False)
    coin = Unicode(default='')

    class Meta:
        db_table = 'tweet'


async def create_db_tables():
    async with create_engine(user='youpsla',
                            database='deviant',
                            host='127.0.0.1',
                            password='372010',
                            port=5432) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine
        mgr.create_tables()

        await User.objects.create()
        await Tweet.objects.create()

        

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_db_tables())
