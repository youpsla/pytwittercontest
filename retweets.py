import asyncio
import logging
import operator
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import tweepy
from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager

from models import Tweet, User

USER_SCREEN_NAME = "deviantcoin"
TWEET_ID = "1175036755311046656"
### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth_handler=auth, retry_count=3)


FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s —  %(funcName)s - %(levelname)s — %(message)s"
)
LOG_FILE = "logs/retweets.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight")
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger


my_logger = get_logger(__name__)


async def get_last_retweet_from_db():
    async with create_engine(
        user="youpsla",
        database="deviant",
        host="127.0.0.1",
        password="372010",
        port=5432,
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine

        last_retweet = await Tweet.objects.filter(retweet__is=True)
    ordered = sorted(last_retweet, key=operator.attrgetter("created_at"), reverse=True)
    if not ordered:
        my_logger.debug("DB is empty")
        return None
    my_logger.debug(f"Last retweet in DB {ordered[0].created_at}")
    print()
    return ordered[0]


async def update_db():
    last_retweet_from_db = await get_last_retweet_from_db()
    retweets_from_twitter = api.retweets(TWEET_ID, count=100)
    if not last_retweet_from_db:
        new_retweets = [
            r
            for r in retweets_from_twitter
            if r.created_at > datetime(2019, 8, 31, 0, 0)
        ]
    else:
        new_retweets = [
            r
            for r in retweets_from_twitter
            if r.created_at > last_retweet_from_db.created_at
        ]
    print(f"{len(new_retweets)} retweets to insert in db")

    async with create_engine(
        user="youpsla",
        database="deviant",
        host="127.0.0.1",
        password="372010",
        port=5432,
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine

        for retweet in new_retweets:
            user, created = await User.objects.get_or_create(id=int(retweet.user.id))
            if created:
                user.name = retweet.user.name
                user.screen_name = retweet.user.screen_name
                user.followers_count = retweet.user.followers_count
                user.statuses_count = retweet.user.statuses_count
                await user.save()

            new_record = Tweet()
            new_record.id = retweet.id
            new_record.text = retweet.text
            new_record.created_at = retweet.created_at
            new_record.user = user
            new_record.retweet = True
            await new_record.save(force_insert=True)


async def main():
    while True:
        await update_db()
        await asyncio.sleep(30)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    loop.run_until_complete(task)
