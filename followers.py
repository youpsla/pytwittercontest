import os

from aiopg.sa import create_engine
from atomdb.sql import SQLModelManager
from tornado import gen
from tweepy import API, Cursor, OAuthHandler, Stream, StreamListener

from models import User

import asyncio

USER_SCREEN_NAME = "deviantcoin"
### Twitter access tokens ###
consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_token_secret = os.environ["TWITTER_TOKEN_SECRET"]


mode_production = False


async def get_followers_and_update_db():
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = API(auth_handler=auth, retry_count=3)

    twitter_followers = []
    if mode_production is True:
        for page in Cursor(api.followers_ids, screen_name=USER_SCREEN_NAME).pages():
            twitter_followers.extend(page)
        with open("test/followers.txt", "x") as f:
            for t in twitter_followers:
                f.write(f"{t}\n")
    else:
        with open("test/followers.txt", "r") as f:
            for l in f:
                twitter_followers.append(l[:-1])

    print(f"Followers count: {len(twitter_followers)}")

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

        users_in_db = await User.objects.filter(follower__is=True)
        ids_in_db = [str(i.id) for i in users_in_db]
        users_to_check = [i for i in twitter_followers if i not in ids_in_db]
        print(f"Followers en twitter account: {len(twitter_followers)}")
        print(f"Followers in DB before update: {len(ids_in_db)}")
        print(f"{len(users_to_check)} to check")

        a = 0
        for i in users_to_check:
            # print(type(i))
            await gen.sleep(1)
            a += 1
            user, created = await User.objects.get_or_create(id=int(i))
            if created:
                # print(f'Create User {user.screen_name}')
                u = api.get_user(i, include_entities=False)
                user.name = u.name
                user.screen_name = u.screen_name
                user.followers_count = u.followers_count
                user.statuses_count = u.statuses_count
                user.follower = True
                print(f"{a} / {len(users_to_check)} : User {user.screen_name} created")
            else:
                # print('User already in db')
                user.follower = True
                print(f"{a} / {len(users_to_check)} : User {user.screen_name} updated")
            await user.save()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(get_followers_and_update_db())
    loop.run_until_complete(task)
