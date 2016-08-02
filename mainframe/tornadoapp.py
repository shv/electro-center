# -*- coding: utf-8 -*-
import datetime
import json
import time
import urllib

# pip install git+https://github.com/evilkost/brukva.git
import brukva
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.httpclient
import tornado.template


from django.conf import settings

from django.forms.models import model_to_dict
from django.utils.module_loading import import_module
session_engine = import_module(settings.SESSION_ENGINE)

from django.contrib.auth.models import User

from mainframe.models import Node, Lamp, Zone
from mainframe.views import parse_device_string

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
        status = data.get("status")
        level = data.get("level")
        if object_type == "lamp":
            result = self.switch(_id, status, level)
        elif object_type == "zone_lamps":
            result = self.switch_zone_by_lamps(_id, status)
        elif object_type == "all_lamps":
            result = self.switch_all_by_lamps(status)

        # Тут нужно передавать id сокет, чтобы распазнать кому что отправлять
        for node_id in result.keys():
            c.publish(self.channels[node_id], json.dumps({
                "env": "ecc",
                "user_id": self.user.id,
                "node_id": node_id,
                "data": json.dumps(result[node_id]),
            }))


    def switch(self, lamp_id, status, level):
        """По одной лампе в формате запроса: ?9=true
        """
        lamp = Lamp.objects.get(id=lamp_id, node__owner=self.user)
        node = lamp.node
        if level is not None and int(level) <= 100 and int(level) >= 0:
            lamp.level = level

        if status is not None:
            lamp.on = True if status == 'on' else False

        lamp.save()

        result = {node.id: []}
        lamp = Lamp.objects.get(id=lamp_id)
        l = model_to_dict(lamp, fields=[], exclude=[])
        l['object_type'] = 'lamp'
        result[node.id].append(l)

        return result


    def switch_zone_by_lamps(self, zone_id, status):
        """Работа с зоной по одной лампе, пока ардуинка не поддерживает много параметров
           TODO отпралять в разные очереди редиса
        """

        zone = Zone.objects.get(id=zone_id, owner=self.user)
        for lamp in zone.lamps.all():
            node = lamp.node
            lamp.on = True if status == 'on' else False
            lamp.save()

        result = {}
        for lamp in zone.lamps.all():
            l = model_to_dict(lamp, fields=[], exclude=[])
            l['object_type'] = 'lamp'
            if lamp.node_id not in result:
                result[lamp.node_id] = []
            result[lamp.node_id].append(l)

        return result


    def switch_all_by_lamps(self, status):
        result = {}
        for node in Node.objects.filter(owner=self.user).all():
            for lamp in node.lamp_set.all():
                node = lamp.node
                lamp.on = True if status == 'on' else False
                lamp.save()

            for lamp in node.lamp_set.all():
                l = model_to_dict(lamp, fields=[], exclude=[])
                l['object_type'] = 'lamp'
                if lamp.node_id not in result:
                    result[lamp.node_id] = []
                result[lamp.node_id].append(l)

        return result


    def show_new_message(self, result):
        body = json.loads(result.body)
        data = body["data"]
        self.write_message(str(data))

    def on_close(self):
        try:
            pass
            # self.client.unsubscribe(self.channel)
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
                print 'connection {} opened...'.format(self.node.token)
                self.write_message("The server says: 'Hello'. Connection {} was accepted.".format(self.node.token))
        except:
            print 'Wrong token, connection closed...'
            self.close()
            return
        self.channel = 'node_%d_messages' % self.node.id
        self.client.subscribe(self.channel)
        self.client.listen(self.show_new_message)

    def show_new_message(self, result):
        self.write_message(str(result.body))

    def on_message(self, message):
        print "Message %s" % message
        data = parse_device_string(message)
        self.node.apply_data(data, lazy=True)

        self.write_message("The server says: " + message + " back at. " + "Results")

        c.publish(self.channel, json.dumps({
            "sender": self.node.id,
            "text": message,
        }))

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
        print 'connection closed...'

class Application(tornado.web.Application):
    def __init__(self):
        handlers = (
            (r"/", MainHandler),
            (r'/ws', ECCHandler),
            (r'/ws/([0-9a-f\-]+)', APIHandler),
        )

        tornado.web.Application.__init__(self, handlers, debug=settings.DEBUG)



application = Application()
