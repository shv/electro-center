# -*- coding: utf-8 -*-
import datetime
import json
import time
import urllib

# pip install git+https://github.com/evilkost/brukva.git
import brukva
import tornado.web #pip install tornado
import tornado.websocket
import tornado.ioloop
import tornado.httpclient
import tornado.template


from django.conf import settings

from django.utils.module_loading import import_module
session_engine = import_module(settings.SESSION_ENGINE)

from django.contrib.auth.models import User

from mainframe.models import Node, Lamp, Zone
from mainframe.views import parse_device_string
from mainframe.utils import switch, switch_zone_by_lamps, switch_all_by_lamps, parse_device_string, generate_device_string

c = brukva.Client()
c.connect()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        loader = tornado.template.Loader(".")
        self.write(loader.load("mainframe/templates/index.html").generate())

class ECCHandler(tornado.websocket.WebSocketHandler):
    # ECC API
    channels = {}
    def __init__(self, *args, **kwargs):
        super(ECCHandler, self).__init__(*args, **kwargs)
        self.client = brukva.Client()
        self.client.connect()

    def open(self):
        session_key = self.get_cookie(settings.SESSION_COOKIE_NAME)
        session = session_engine.SessionStore(session_key)
        try:
            self.user_id = session["_auth_user_id"]
        except (KeyError, User.DoesNotExist):
            self.close()
            return

        self.user = User.objects.get(id=self.user_id)
        for node in Node.objects.filter(owner=self.user_id).all():
            self.channels[node.id] = 'node_%d_messages' % node.id
            self.client.subscribe(self.channels[node.id])
            self.client.listen(self.show_new_message)


    def check_origin(self, origin):
        return True

    def handle_request(self, response):
        pass

    def on_message(self, message):
        if not message:
            return
        if len(message) > 10000:
            return
        data = json.loads(message)
        object_type = data.get("object_type")
        _id = data.get("id")
        status = data.get("on")
        level = data.get("level")

        # Применяем асинхронно изменения
        http_client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(
            "".join([
                        settings.API_SYNC_URL,
                        str(self.node.token),
                    ]),
            method="POST",
            body=urllib.urlencode({
                "api_key": settings.API_KEY,
                "data": json.dumps(data),
            })
        )
        http_client.fetch(request, self.handle_request)

        if object_type == "lamp":
            result = switch(self.user, _id, status, level)
        elif object_type == "zone_lamps":
            result = switch_zone_by_lamps(self.user, _id, status)
        elif object_type == "all_lamps":
            result = switch_all_by_lamps(self.user, status)

        # Тут нужно передавать id сокет, чтобы распазнать кому что отправлять
        for node_id in result.keys():
            c.publish(self.channels[node_id], json.dumps({
                "env": "ecc",
                "user_id": self.user.id,
                "node_id": node_id,
                "data": result[node_id],
            }))

    def show_new_message(self, result):
        body = json.loads(result.body)
        data = body["data"]
        self.write_message(json.dumps(data))

    def on_close(self):
        try:
            for node_id in self.channels:
               self.client.unsubscribe(self.channels[node_id])
        except AttributeError:
            pass
        def check():
            pass
            # if self.client.connection.in_progress:
            #     tornado.ioloop.IOLoop.instance().add_timeout(
            #         datetime.timedelta(0.00001),
            #         check
            #     )
            # else:
            #     self.client.disconnect()
        tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(0.00001),
            check
        )

class APIHandler(tornado.websocket.WebSocketHandler):
    # Arduino api
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)
        self.client = brukva.Client()
        self.client.connect()

    def open(self, token):
        try:
            node = Node.objects.get(token=token)
            if node:
                self.node = node
        except:
            self.close()
            return
        self.channel = 'node_%d_messages' % self.node.id
        self.client.subscribe(self.channel)
        self.client.listen(self.show_new_message)
        # Тут нужно синхронизировать данные, например отправлять ноде,
        #   либо наоборот при коннекте получать от ноды

    def show_new_message(self, result):
        # Реакция на сообщение в редисе
        data = json.loads(result.body)
        if not (data["env"] == "node" and data["node_id"] == self.node.id):
            # Свои сообщения игнорируем
            self.write_message(str(generate_device_string(data["data"])))

    def check_origin(self, origin):
        return True

    def handle_request(self, response):
        # попробуем дожидаться ответа от базы и только после этого отправлять сообщение в вебморду
        result = json.loads(response.body)
        c.publish(self.channel, json.dumps({
            "env": "node",
            "node_id": self.node.id,
            "data": result,
        }))


    def on_message(self, message):
        if not message:
            return
        if len(message) > 10000:
            return
        data = parse_device_string(message)
        # API внесения изменения в базу
        # Так как тут мы не знаем id ламп и сенсоров, то сообщения в вебморды пойдут после ответа от базы
        http_client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(
            "".join([
                        settings.API_SYNC_URL,
                        str(self.node.token),
                    ]),
            method="POST",
            body=urllib.urlencode({
                "api_key": settings.API_KEY,
                "data": json.dumps(data),
            })
        )
        http_client.fetch(request, self.handle_request)

        # Сообщение отправляется во все другие сокеты
        # Нужно сделать выборку по ноде и юзеру и отправлять только в нужные каналы
        # Так же нужно на этот сокет подсадить вебморду
        # Если нужно будет масштабировать, то придется использовать очереди


    def on_close(self):
        try:
            self.client.unsubscribe(self.channel)
        except AttributeError:
            pass
        def check():
            if self.client.connection.in_progress:
                tornado.ioloop.IOLoop.instance().add_timeout(
                    datetime.timedelta(0.00001),
                    check
                )
            else:
                self.client.disconnect()
        tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(0.00001),
            check
        )

class Application(tornado.web.Application):
    def __init__(self):
        handlers = (
            (r"/", MainHandler),
            (r'/ws', ECCHandler),
            (r'/ws/([0-9a-f\-]+)', APIHandler),
        )

        tornado.web.Application.__init__(self, handlers, debug=settings.DEBUG)


application = Application()
