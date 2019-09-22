import asyncio
import json
import os
from collections import Counter
from functools import reduce

import enaml
import tornado.ioloop
import tornado.web
import tornado.websocket
from aiopg.sa import create_engine
from atomdb.sql import SQLModel, SQLModelManager, SQLModelSerializer
from sqlalchemy import func, select
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from web.core.app import WebApplication

from models import Tweet, User

with enaml.imports():
    from viewer import Viewer


log = tornado.web.app_log


# TODO synthèse des votes par coin
# TODO Control if user has already voted. prevent multi voting
# TODO Implement db regular backup: cron + pg_dump
# TODO FIx connection when server restart. Wensocket client pull all the time
# TODO Add "updated_at" field to User. Add observer function column in datatables


# Holds the rendered view so a websocket can retrieve it later
CACHE = {}


class ViewerHandler(tornado.web.RequestHandler):

    async def get(self): # TODO Manage websockets when browser not refreshed
        viewer = Viewer(request=self.request, response=self, datas=[])
        
        tornado.log.gen_log.debug("I'm doing some stuff")
        tmp_list = []
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="372010", port=5432
        ) as engine:
            SQLModelManager.instance().database = engine
            coins = await Tweet.objects.all()
            coins_list = Counter([c.coin for c in coins if c.coin != ''])
            for k,v in coins_list.items():
                tmp_list.append({'coin': k, 'nb':v})
            viewer.coinsleaderboard.leaderboard_list = tmp_list
        
        CACHE[viewer.ref] = viewer
        self.write(viewer.render())

class DatasHandler(tornado.web.RequestHandler):

    datas = {}
    datas["data"] = []

    async def prepare(self):
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="372010", port=5432
        ) as engine:
            SQLModelManager.instance().database = engine
            users = await User.objects.all()
            for u in users:
                tmp_dict = {}
                tmp_dict["Name"] = u.screen_name
                tmp_dict["Tweets"] = u.statuses_count
                tmp_dict["Followers"] = u.followers_count
                tmp_dict["id"] = str(u.id)
                tmp_dict["Follow"] = u.follower

                u.tweets = await Tweet.objects.filter(user=u.id)
                if True in [i.retweet for i in u.tweets]:
                    tmp_dict["Retweet"] = True

                tmp = [i.coin for i in u.tweets if i.coin != '']
                log.debug(f'tmp :  {len(tmp)}')
                if len(tmp) == 1:
                    tmp_dict["Coin"] = tmp[0]

                self.datas["data"].append(tmp_dict)

    async def get(self):
        self.write(json.dumps(self.datas))
        self.datas["data"] = []


class WsHandler(tornado.websocket.WebSocketHandler):
    viewer = None

    # async def get_coins_leaderboard(self):
    #     tmp_list = []
    #     async with create_engine(
    #         user="youpsla", database="deviant", host="127.0.0.1", password="372010", port=5432
    #     ) as engine:
    #         SQLModelManager.instance().database = engine
    #         coins = await Tweet.objects.all()
    #         coins_list = Counter([c.coin for c in coins if c.coin != ''])
    #         print(json.dumps(coins_list))
    #         for k,v in coins_list.items():
    #             tmp_list.append({'coin': k, 'nb':v})
    #         self.viewer.coinsleaderboard.leaderboard_list = tmp_list
            
     

    async def get_user_tweets(self, userid):
        tweetslist = []
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="372010", port=5432
        ) as engine:
            SQLModelManager.instance().database = engine
            tweets = await Tweet.objects.filter(user=userid)
            for t in tweets:
                try:
                    username = str(t.user.screen_name)
                except:
                    username = ''

                tweetslist.append(
                    {
                        "text": t.text,
                        "coin": str(t.coin),
                        "retweet": str(t.retweet),
                        "date": str(t.created_at),
                        "id": str(t.id),
                        "user": username
                    }
                )
            self.viewer.tweetsdetails.tweets_list = tweetslist

    async def get_summary_report(self):
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="372010", port=5432
        ) as engine:
            SQLModelManager.instance().database = engine

            followers = await User.objects.filter(follower__is=True)
            followers_count = len(followers)
            followers_count_users_id = [i.id for i in followers]
            print(f"nb followers : {followers_count}")

            coins = await Tweet.objects.filter(coin__gt='')
            coins_count_users_id = {i.user.id for i in coins}
            coins_count = len(coins_count_users_id)
            print(f"coins count: {coins_count}")

            retweets = await Tweet.objects.filter(retweet__is=True)
            retweets_count_users_id = {i.user.id for i in retweets}
            retweets_count = len(retweets_count_users_id)
            print(f"retweets count: {retweets_count}")

            listes = [
                followers_count_users_id,
                coins_count_users_id,
                retweets_count_users_id,
            ]
            total_liste = reduce(set.intersection, [set(l_) for l_ in listes])
            log.debug(total_liste)

            summary_report = [
                {"name": "Followers", "nb": followers_count},
                {"name": "Users have retweet", "nb": retweets_count},
                {"name": "Users haave coined", "nb": coins_count},
                {"name": "Users qualified", "nb": len(total_liste)},
            ]

            self.viewer.summaryreport.summary_report_list = summary_report

    async def on_message(self, message):
        print(f"WS message : {message}")
        change = tornado.escape.json_decode(message)

        if change["event"] == "user_tweets":
            userid = change["userid"]
            await self.get_user_tweets(userid)

        # if change["event"] == "update_followers":
        #     self.viewer.updatefollowers.update_button.attrs = {"disabled": "True"}
        #     await get_followers_and_update_db(self.viewer)
        #     del self.viewer.updatefollowers.update_button.attrs

        if change["event"] == "update_summary_report":
            await self.get_summary_report()

    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        # Store the viewer in the cache

        if self.viewer is None:
            ref = self.get_argument(("ref"))
        self.viewer = CACHE[ref]
        self.viewer.observe("modified", self.on_dom_modified)

    def on_dom_modified(self, change):
        """ When an event from enaml occurs, send it out the websocket
        so the client's browser can update accordingly.
        """
        log.debug(f"Update from enaml: {change}")
        self.write_message(json.dumps(change["value"]))


class StaticFiles(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )


def run_web_app():
    enaml_app = WebApplication()
    # Start the tornado app
    app = tornado.web.Application(
        [
            (r"/", ViewerHandler),
            (r"/datas", DatasHandler),
            (r"/ws", WsHandler),
            (r"/static/(.*)", StaticFiles, {"path": "static/"}),
        ],
        debug=True,

    )
    app.listen(8888)

    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.start()

if __name__ == "__main__":
    run_web_app()
