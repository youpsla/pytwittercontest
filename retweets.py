import tweepy
import asyncio
import os
from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager
from models import User, Tweet
import operator
from datetime import datetime


USER_SCREEN_NAME = "deviantcoin"
TWEET_ID = '1174595009674448898'
### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth_handler=auth, retry_count=3)


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
    
        last_retweet = await Tweet.objects.all()
    ordered = sorted(last_retweet, key=operator.attrgetter('created_at'), reverse = True)
    if not ordered:
        print('Database is empty')
        return None
    print(f'Last tweet in DB {ordered[0].created_at}')
    return ordered[0]


async def update_db():
    last_retweet_from_db = await get_last_retweet_from_db()
    retweets_from_twitter = api.retweets(TWEET_ID, count = 100)
    #print(type(last_retweet_from_db.created_at))
    if not last_retweet_from_db:
        new_retweets = [r for r in retweets_from_twitter if r.created_at > datetime(2019, 8, 31,0,0)]
    else:
        new_retweets = [r for r in retweets_from_twitter if r.created_at > last_retweet_from_db.created_at]
    print(f'{len(new_retweets)} retweets to insert in db')


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
        await asyncio.sleep(20)
        await update_db()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    loop.run_until_complete(task)