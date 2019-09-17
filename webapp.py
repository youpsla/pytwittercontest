import os
import json
import enaml
import tornado.web
import tornado.websocket
import tornado.ioloop
from tornado.escape import json_decode
from web.core.app import WebApplication

from models import Tweet, User

from aiopg.sa import create_engine

import asyncio

from atomdb.sql import SQLModel, SQLModelManager, SQLModelSerializer

from tornado.ioloop import IOLoop

from functools import reduce


with enaml.imports():
    from viewer import Viewer


log = tornado.web.app_log

# Holds the rendered view so a websocket can retrieve it later
CACHE = {}


class ViewerHandler(tornado.web.RequestHandler):

    async def get(self):
        viewer = Viewer(
            request = self.request,
            response = self,
            datas = []
        )

        CACHE[viewer.ref] = viewer

        self.write(viewer.render())


        # if len(CACHE) > 0:
        #     viewer = CACHE["reference"]
        #     print(f"Viewer cache ref : {viewer.ref}")
        # else:
        #     print('Instance not in cache')
        #     viewer = Viewer(request=self.request, response=self)
        #     CACHE["reference"] = viewer
        # self.write(viewer.render())



class DatasHandler(tornado.web.RequestHandler):

    datas = {}
    datas["data"] = []

    async def prepare(self):
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
        ) as engine:
            SQLModelManager.instance().database = engine
            users = await User.objects.all()
            for u in users:
                tmp_dict = {}
                tmp_dict["Name"] = u.screen_name
                tmp_dict["Tweets"] = u.statuses_count
                tmp_dict["Followers"] = u.followers_count
                tmp_dict["id"] = str(u.id)
                tmp_dict["follow"] = str(u.follower)

                u.tweets = await Tweet.objects.filter(user=u.id)
                if True in [i.retweet for i in u.tweets]:
                    tmp_dict["Retweet"] = True

                if True in [i.vote for i in u.tweets]:
                    tmp_dict["Vote"] = True

                self.datas["data"].append(tmp_dict)

    async def get(self):
        self.write(json.dumps(self.datas))
        self.datas["data"] = []


class TestHandler(tornado.web.RequestHandler):

    datas = {}
    datas["data"] = []

    async def prepare(self):
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
        ) as engine:
            SQLModelManager.instance().database = engine
            q = Tweet.objects.table.join(User.objects.table).select(use_labels=True)

            for row in await Tweet.objects.fetchall(q):
                # Restore each manually, it handles pulling out the fields that are it's own
                tweet = await Tweet.restore(row)
                print(tweet.text)

                user = await User.restore(row)
                print(user.name)


class TweetsPerUserHandler(tornado.web.RequestHandler):
    async def post(self):

        ref = self.get_argument("ref")
        args = tornado.escape.json_decode(self.request.body)
        ref = args["ref"]
        print(f"ref : {ref}")

        query = '//*[@ref="{}"]'.format(args["ref"])
        print(f"query : {query}")

        node = await Viewer.xpath(Viewer, query, first=True)

        example_response = {}
        example_response["name"] = "example"
        example_response["width"] = 1020

        # self.write(json.dumps(example_response))

        # self.write(viewer.args['ref'])


from sqlalchemy import select, func
from services import get_followers_and_update_db
class WsHandler(tornado.websocket.WebSocketHandler):
    viewer = ''


    async def get_user_tweets(self, userid):
        tweetslist = []
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
        ) as engine:
            SQLModelManager.instance().database = engine
            tweets = await Tweet.objects.filter(user=userid)
            for t in tweets:
                print(t.text)
                tweetslist.append(
                    {
                        "text": t.text,
                        "vote": str(t.vote),
                        "retweet": str(t.retweet),
                        "date": str(t.created_at),
                        "id": str(t.id),
                    }
                )
            print(f'tweet list{tweetslist}')
            CACHE["reference"].tweetsdetails.tweets_list = tweetslist


    async def get_summary_report(self):
        async with create_engine(
            user="youpsla", database="deviant", host="127.0.0.1", password="", port=5433
        ) as engine:
            SQLModelManager.instance().database = engine
            #q = User.objects.table.select(follower__is = False)
            # q = select([func.count()]).select(User.objects.table).filter(User.objects.table.vote == True)
            #dede = q.count()
            #print(f'vote count {dede}')

            followers = await User.objects.filter(follower__is = True)
            followers_count = len(followers)
            followers_count_users_id = [i.id for i in followers]
            print(f'nb followers : {followers_count}')
            
            votes = await Tweet.objects.filter(vote__is = True)
            votes_count_users_id = set([i.user for i in votes])
            votes_count = len(votes_count_users_id)
            print(f'votes count: {votes_count}')

            retweets = await Tweet.objects.filter(retweet__is = True)
            retweets_count_users_id = set([i.user for i in retweets])
            retweets_count = len(retweets_count_users_id)
            print(f'retweets count: {retweets_count}')

            listes = [followers_count_users_id, votes_count_users_id, retweets_count_users_id]
            total_liste = reduce(set.intersection, [set(l_) for l_ in listes])

            summary_report = [{'name': 'Followers', 'nb': followers_count},
            {'name': 'Users have retweet', 'nb': retweets_count},
            {'name': 'Users haave voted', 'nb': votes_count},
            {'name': 'Users qualified', 'nb': len(total_liste)}
            ]

            CACHE["reference"].summaryreport.summary_report_list = summary_report




            #for row in await User.objects.fetchall(q):
            #    print(row)

    async def on_message(self, message):
        print(f"WS message : {message}")
        change = tornado.escape.json_decode(message)
        
        if change['event'] == 'user_tweets':
            print('enter user_tweets')
            print(change)
            userid = change['userid']
            await self.get_user_tweets(userid)

        if change['event'] == 'update_followers':
            self.viewer.updatefollowers.update_button.attrs = {'disabled' : 'True'}
            await get_followers_and_update_db(self.viewer)
            del self.viewer.updatefollowers.update_button.attrs 

        if change['event'] == 'update_summary_report':
            await self.get_summary_report()
            

    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        # Store the viewer in the cache
        ref = self.request.arguments
        print(f'REF REF REF : {ref}')

        self.viewer = CACHE['reference']
        args = self.open_args
        print('local')
        print(locals().keys())
        # print(f"args dans open websocket : {args}")
        self. viewer.observe("modified", self.on_dom_modified)

    def on_dom_modified(self, change):
        """ When an event from enaml occurs, send it out the websocket
        so the client's browser can update accordingly.
        """
        print(f'on dom modified {change}')
        log.debug(f"Update from enaml: {change}")
        self.write_message(json.dumps(change["value"]))



class StaticFiles(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )


def run_web_app():
    print("Enter run_web_app")

    enaml_app = WebApplication()
    # print("dede")
    # Start the tornado app
    app = tornado.web.Application(
        [
            (r"/", ViewerHandler),
            (r"/datas", DatasHandler),
            (r"/tweetsperuser", TweetsPerUserHandler),
            (r"/test", TestHandler),
            (r"/ws", WsHandler),
            (r"/static/(.*)", StaticFiles, {"path": "static/"}),
        ]
    )
    app.listen(8888)

    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.start()

    print("End of run_web_app")


if __name__ == "__main__":
    run_web_app()

