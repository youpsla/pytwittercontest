import tweepy
import asyncio
import os
from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager
from models import User, Tweet
import operator


USER_SCREEN_NAME = "deviantcoin"
### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth_handler=auth, retry_count=3)


async def get_last_retweet_from_db():
    print('dada')
    async with create_engine(
        user="youpsla",
        database="deviant",
        host="127.0.0.1",
        password="372010",
        port=5432,
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine
    
        last_retweet = await Tweet.objects.all()
    ordered = sorted(last_retweet, key=operator.attrgetter('created_at'), reverse = True)
    for i in ordered:
        print(i.created_at)
    print(ordered[0])
    return ordered[0]


async def update_db():
    async with create_engine(
        user="youpsla",
        database="deviant",
        host="127.0.0.1",
        password="372010",
        port=5432,
    ) as engine:
        mgr = SQLModelManager.instance()
        mgr.database = engine
        mgr.create_tables()


        last_retweet_from_db = await get_last_retweet_from_db()
        retweets_from_twitter = api.retweets('1174595009674448898', count = 10)
        new_retweets = [r for r in retweets_from_twitter if r.created_at > last_retweet_from_db.created_at]
        for i in new_retweets:
            print(i.created_at)
        #print(new_retweets)

        for retweet in new_retweets:
            new_record = Tweet()
            new_record.id = retweet.id
            new_record.text = retweet.text
            new_record.created_at = retweet.created_at
            new_record.user = retweet.user





if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(update_db())
    loop.run_until_complete(task)