from webapp import run_web_app
from models import create_db_tables
from services import start_tweets_stream
import threading, queue
import tornado

import asyncio

# loop = asyncio.get_event_loop()
# print(loop)

# ioloop = tornado.ioloop.IOLoop.instance()

def web_thread():
    #loop = asyncio.new_event_loop()
    #asyncio.set_event_loop(loop)
    print('Run web_thread service')
    #loop.run_until_complete(run_web_app(loop))
    run_web_app()
    # run_web_app()
    
    print(loop)

def db_thread(db='deviant'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print('Run db_thread service')

    loop.run_until_complete(create_db(db))

def tweepy_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f'loop in tweepy_thread: {asyncio.get_event_loop()}')
    print('Run tweepy_thread service')

    loop.run_until_complete(start_tweets_stream())

    

if __name__ == "__main__":

    # for target in (web_thread, db_thread, tweepy_thread):
    #     thread = threading.Thread(target=target)
    #     thread.daemon = True
    #     thread.start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_tweets_stream())

    print(f'Maint Thread loop: {loop}')
    #tasks = [asyncio.create_task(start_tweets_stream()),]
    #loop.run_until_complete(asyncio.gather(*tasks))

    #thread_db = threading.Thread(target=db_thread())
    #thread_db.start()

    #thread_web = threading.Thread(target=web_thread())
    #thread_web.start()

    #thread_tweepy = threading.Thread(target=tweepy_thread())
    #thread_tweepy.start()

    #futures = [start_tweets_stream()]
    #loop.run_until_complete(asyncio.gather(*futures))
