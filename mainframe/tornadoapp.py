# -*- coding: utf-8 -*-
# WebSocket Tornado for Django: https://habrahabr.ru/post/160123/
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

from django.utils import timezone
from django.utils.module_loading import import_module
session_engine = import_module(settings.SESSION_ENGINE)

from django.contrib.auth.models import User

from mainframe.models import Node, Lamp, Zone
from mainframe.utils import parse_device_string, generate_device_string, stats_decorator

c = brukva.Client()
c.connect()

class TesterHandler(tornado.web.RequestHandler):
    def get(self):
        loader = tornado.template.Loader(".")
        template = loader.load("mainframe/templates/index.html")
        self.write(template.generate(settings=settings))

class ECCHandler(tornado.websocket.WebSocketHandler):
    # ECC API
    channels = {}
    def __init__(self, *args, **kwargs):
        super(ECCHandler, self).__init__(*args, **kwargs)
        self.client = brukva.Client()
        self.client.connect()

    @stats_decorator
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


    @stats_decorator
    def check_origin(self, origin):
        return True

    @stats_decorator
    def handle_request(self, response):
        result = json.loads(response.body)
        # print result;
        for node_id in result.keys():
            c.publish(self.channels[int(node_id)], json.dumps({
                "env": "ecc",
                "node_id": int(node_id),
                "data": result[node_id],
            }))

    @stats_decorator
    def on_message(self, message):
        if not message:
            return
        if len(message) > 10000:
            return
        data = json.loads(message)
        # Применяем асинхронно изменения
        http_client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(
            "".join([
                        settings.ECC_SYNC_URL
                    ]),
            method="POST",
            body=urllib.urlencode({
                "api_key": settings.API_KEY,
                "user_id": self.user.id,
                "data": json.dumps(data),
            })
        )
        http_client.fetch(request, self.handle_request)


    @stats_decorator
    def show_new_message(self, result):
        body = json.loads(result.body)
        data = body["data"]
        self.write_message(json.dumps(data))

    @stats_decorator
    def on_close(self):
        for node_id in self.channels:
            try:
               self.client.unsubscribe(self.channels[node_id])
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

class APIHandler(tornado.websocket.WebSocketHandler):
    # Arduino api
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)
        self.client = brukva.Client()
        self.client.connect()
        self.io_loop = tornado.ioloop.IOLoop.instance()
        # Ниже принудительный сброс флага online при рестарте приложения (пока так)
        Node.objects.filter(online=True).update(online=False)


    @stats_decorator
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
        # Инициализация ноды при подключении.
        # Нужно добавить режим чтения ноды при подключении в зависимости от ноды
        result = []
        for lamp in self.node.lamp_set.all():
            result.append({
                'on': lamp.on,
                'auto': lamp.auto,
                'object_type': 'lamp',
                'id': lamp.id,
                'external_id': lamp.external_id,
                'level': lamp.level if lamp.dimmable else ''
            })
        self.node.last_answer_time = timezone.now()
        self.node.online = True
        self.node.save()
        c.publish(self.channel, json.dumps({
            "env": "node",
            "node_id": self.node.id,
            "data": [{
                    "id": self.node.id,
                    "object_type": "node",
                    "online": True,
                    'last_answer_time': self.node.last_answer_time.isoformat()
            }],
        }))

        # https://github.com/tornadoweb/tornado/issues/1763
        if self.node.pinging:
            self.ping_timeout = self.io_loop.call_later(
                delay=self.get_ping_timeout(initial=True),
                callback=self._send_ping,
            )

        self.write_message(str(generate_device_string(result)))



    @stats_decorator
    def show_new_message(self, result):
        # Реакция на сообщение в редисе
        data = json.loads(result.body)
        # print data
        if not (data["env"] == "node" and data["node_id"] == self.node.id):
            # Свои сообщения игнорируем
            self.write_message(str(generate_device_string(data["data"])))

    @stats_decorator
    def check_origin(self, origin):
        return True

    @stats_decorator
    def handle_request(self, response):
        # попробуем дожидаться ответа от базы и только после этого отправлять сообщение в вебморду
        result = json.loads(response.body)
        c.publish(self.channel, json.dumps({
            "env": "node",
            "node_id": self.node.id,
            "data": result,
        }))


    @stats_decorator
    def on_message(self, message):
        if not message:
            return
        if len(message) > 10000:
            return
        # print message
        data = parse_device_string(message)
        # print data
        # API внесения изменения в базу
        # Так как тут мы не знаем id ламп и сенсоров, то сообщения в вебморды пойдут после ответа от базы
        http_client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(
            "".join([
                        settings.API_SYNC_URL
                    ]),
            method="POST",
            body=urllib.urlencode({
                "api_key": settings.API_KEY,
                "node_id": self.node.id,
                "data": json.dumps(data),
            })
        )
        http_client.fetch(request, self.handle_request)

        # Сообщение отправляется во все другие сокеты
        # Нужно сделать выборку по ноде и юзеру и отправлять только в нужные каналы
        # Так же нужно на этот сокет подсадить вебморду
        # Если нужно будет масштабировать, то придется использовать очереди


    @stats_decorator
    def on_close(self):
        self.node.online = False
        self.node.save()
        c.publish(self.channel, json.dumps({
            "env": "node",
            "node_id": self.node.id,
            "data": [{
                    "id": self.node.id,
                    "object_type": "node",
                    "online": False,
                    'last_answer_time': self.node.last_answer_time.isoformat()
            }],
        }))
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

    @staticmethod
    def get_ping_timeout(initial=False):
        """
        Args:
            initial: First is true when it is initial ping to be sent
        """
        return 5

    @staticmethod
    def get_pong_timeout():
        """
        Returns pong timeout for pong
        """
        return 2

    def on_pong(self, data):
        print('Received pong')
        if hasattr(self, 'ping_timeout'):
            # clear timeout set by for ping pong (heartbeat) messages
            self.io_loop.remove_timeout(self.ping_timeout)

        # send new ping message after `get_ping_timeout` time
        self.ping_timeout = self.io_loop.call_later(
            delay=self.get_ping_timeout(),
            callback=self._send_ping,
        )

    def _send_ping(self):
        """
        Send ping message to client.

        Creates a time out for pong message.
        If timeout is not cleared then closes the connection.
        """
        print('Sending ping')
        self.ping(b'a')
        self.ping_timeout = self.io_loop.call_later(
            delay=self.get_pong_timeout(),
            callback=self._connection_timeout,
        )

    def _connection_timeout(self):
        """ If no pong message is received within the timeout then close the connection """
        print("Ping pong timeout")
        self.close(None, 'Connection Timeout')



class Application(tornado.web.Application):
    def __init__(self):
        handlers = (
            (r"/ws-test", TesterHandler),
            (r'/ws', ECCHandler),
            (r'/ws/([0-9a-f\-]+)', APIHandler),
        )

        tornado.web.Application.__init__(self, handlers, debug=settings.DEBUG)


application = Application()
