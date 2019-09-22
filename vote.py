import tweepy
import asyncio
import os
from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager
from tweepy import API, Cursor, OAuthHandler, Stream, StreamListener
from models import User, Tweet
import re
import json
from datetime import datetime


USER_SCREEN_NAME = "deviantcoin"
VOTE_HASHTAG = '#deviantvotetest'

### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth_handler=auth, retry_count=3)



def tdate_to_timestamp(tdate):
    return datetime.strptime(tdate, "%a %b %d %H:%M:%S +0000 %Y")

def is_vote(text):
    pattern = "(%s)\s+(\${1}\w+)" % (VOTE_HASHTAG)
    m = re.match(pattern, text)
    if m:
        result = m.groups()
        if result[0] is not None:
            if result[1] is not None:
                return (True, result[1])
    return (None, '')

async def update_db(data):
    parsed = json.loads(data)

    vote, coin = is_vote(parsed["text"])
    if None in [vote, coin]:
        return
    
    print(f'New vote detected : {coin}')

    async with create_engine(
        user="youpsla",
        database="deviant",
        host="127.0.0.1",
        password="372010",
        port=5432,
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine

        user, created = await User.objects.get_or_create(id=int(parsed['id']))
        if created:
            user.name = parsed["user"]["name"]
            user.screen_name = parsed["user"]["screen_name"]
            user.followers_count = parsed["user"]["followers_count"]
            user.statuses_count = parsed["user"]["statuses_count"]
            await user.save()
            

            new_record = Tweet()
            new_record.id = parsed["id"]
            new_record.text = parsed["text"]
            new_record.created_at = tdate_to_timestamp(parsed["created_at"])
            new_record.user = user
            new_record.coin = coin
            await new_record.save(force_insert=True)


class TweetstListener(StreamListener):

    def on_data(self, raw_data):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.process_data(raw_data))
        loop.run_until_complete(task)

    async def process_data(self, raw_data):
        await update_db(raw_data)

    def on_error(self, status):
        print(f"Status: {status}")


def start_tweets_stream():
    print("Start start_tweets_stream")

    listener = TweetstListener()
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = Stream(auth, listener)
    stream.filter(track=[VOTE_HASHTAG])


if __name__ == "__main__":
    start_tweets_stream()