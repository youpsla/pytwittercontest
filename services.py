from __future__ import absolute_import, print_function

import asyncio
import datetime
import json
import os
import re

from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager
from tweepy import OAuthHandler, Stream, StreamListener, API, Cursor

from models import Tweet, User

### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]

USER_SCREEN_NAME = 'clamienne'


def is_vote(text):
    pattern = "^(#devianttest)\s+(\${1}\w+)"
    m = re.match(pattern, text)
    if m:
        result = m.groups()
        print(f'result {result}')
        if result[0] is not None:
            if result[1] is not None:
                print(f'VOOOOTE {text}')
                return True
            return None


def is_retweet(text):
    pattern = "(RT|rt)( @\w*)?[: ]"
    return re.match(pattern, text)


def tdate_to_timestamp(tdate):
    return datetime.datetime.strptime(tdate, "%a %b %d %H:%M:%S +0000 %Y")


from tornado import gen
async def get_followers_and_update_db(viewer):
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = API(auth_handler=auth, retry_count=3)

    ids = []
    # for page in Cursor(api.followers_ids, screen_name="DeviantCoin").pages():
    for page in Cursor(api.followers_ids, screen_name=USER_SCREEN_NAME).pages():
        ids.extend(page)

    print(f'Followers count: {len(ids)}')

    async with create_engine(
        user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine
        mgr.create_tables()

        a = 0
        for i in ids:
            await gen.sleep(1)
            a += 1
            user, created = await User.objects.get_or_create(id=i)
            asyncio.sleep(1)
            viewer.updatefollowers.processed = a
            if created:
                # u = api.lookup_users(user_ids = [i], include_entities = False)
                u = api.get_user(i, include_entities = False)
                u = u
                user.name = u.name
                user.screen_name = u.screen_name
                user.followers_count = u.followers_count
                user.statuses_count = u.statuses_count
                user.follower = True
            else:
                user.follower = True
            await user.save()

async def control_tweet(data):
    parsed = json.loads(data)

    retweet = False
    vote = False

    if is_retweet(parsed["text"]):
        retweet = True
    if is_vote(parsed["text"]):
        vote = True

    async with create_engine(
        user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine
        mgr.create_tables()

        if retweet or vote:
            user, created = await User.objects.get_or_create(id=parsed["user"]["id"])
            if created:
                user.name = parsed["user"]["name"]
                user.screen_name = parsed["user"]["screen_name"]
                user.followers_count = parsed["user"]["followers_count"]
                user.statuses_count = parsed["user"]["statuses_count"]
                user.follower = False
                await user.save()
            else:
                print("user already exist")

            tweet, created = await Tweet.objects.get_or_create(
                id=parsed["id"],
                text=parsed["text"],
                retweet=retweet,
                vote=vote,
                created_at=tdate_to_timestamp(parsed["created_at"]),
                user=user,
            )

            print("New tweet created in DB")


class TweetstListener(StreamListener):
    """ A listener handles tweets that are received from the stream.
    This is a basic listener that just prints received tweets to stdout.

    """

    def on_data(self, raw_data):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.process_data(raw_data))
        loop.run_until_complete(task)

    async def process_data(self, raw_data):
        await control_tweet(raw_data)

    def on_error(self, status):
        print(f"Status: {status}")


def start_tweets_stream():
    print("Start start_tweets_stream")

    listener = TweetstListener()
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = Stream(auth, listener)
    stream.filter(track=["#bitcoin",])


if __name__ == "__main__":
    start_tweets_stream()
    # loop = asyncio.get_event_loop()
    # task = loop.create_task(get_followers_and_update_db())
    # loop.run_until_complete(task)
    # get_followers_and_insert()

