#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import httplib, urllib
import json
import redis #pip install redis

from django.forms.models import model_to_dict
from django.db.models import Sum, Count, Avg, Min, Max
from django.http import HttpResponse
from django.db import connection
from django.template import loader
from django.utils import timezone
from datetime import timedelta
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview

from .models import Node, Lamp, Zone, Sensor

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = 1

""" Нода может работать в двух режимах:
        Активный (не заполняем хост ноды)
            Нода сама коннектится к сервера
            Нода интересуется у сервера что поменять
            Нода отправляет всю нужную инфу
        Пассивный (нужно указать хост ноды)
            Нода ничего никуда не шлет, а только слушает
            Сервак при каждом изменении пинает ноду
            Сервак сам решает как часто интересоваться статусом ноды
"""

def render(f):
    def tmp(request, *args, **kwargs):
        context = f(request, *args, **kwargs)
        request_user = request.user if request.user.is_authenticated() else None
        context.update(dict(
            zones = Zone.objects.filter(owner=request_user).all(),
            nodes = Node.objects.filter(owner=request_user).all()
        ))

        template = loader.get_template(context['template'])
        return HttpResponse(template.render(context, request))

    return tmp


def render_string(f):
    def tmp(request, *args, **kwargs):
        context = f(request, *args, **kwargs)
        logger.debug(context)
        lamps = []
        for pin in context:
            lamps.append("{:d}:{}:{}:{}".format(pin['pin'], pin.get('on', ''), pin.get('level', ''), pin.get('value', '')))

        return HttpResponse(','.join(lamps))

    return tmp


@render
def index(request):
    request_user = request.user if request.user.is_authenticated() else None
    sensors = Sensor.objects.filter(node__owner=request_user).all()
    return dict(
        template = 'mainframe/index.html',
        sensors = sensors
    )


@render
def zone(request, zone_id):
    request_user = request.user if request.user.is_authenticated() else None
    zone = Zone.objects.get(id=zone_id, owner=request_user)
    for node in zone.nodes():
        if node.host:
            node.refresh_all()

    return dict(
        template = 'mainframe/zone.html',
        zone = zone
    )


@render
def node(request, node_id):
    request_user = request.user if request.user.is_authenticated() else None
    node = Node.objects.get(id=node_id, owner=request_user)
    if node.host:
        node.refresh_all()
    return dict(
        template = 'mainframe/node.html',
        active_menu = 'nodes',
        node = node
    )


@json_view
def lamps(request, node_id):
    request_user = request.user if request.user.is_authenticated() else None
    node = Node.objects.get(id=node_id, owner=request_user)
    if node.host:
        node.refresh_all()

    return [model_to_dict(lamp, fields=[], exclude=[]) for lamp in node.lamp_set.all()]


@json_view
def switch(request, lamp_id, status):
    """По одной лампе в формате запроса: ?9=true
    """
    request_user = request.user if request.user.is_authenticated() else None
    lamp = Lamp.objects.get(id=lamp_id, node__owner=request_user)
    node = lamp.node
    logger.info("Node: %s" % node)
    if node.host:
        action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
        result = node.make_request(action)

        if not result:
            lamp.on = None
            logger.info("%s: %s" % (lamp.pin, lamp.on))
            lamp.save()
    else:
        lamp.on = True if status == 'on' else False
        lamp.save()


    result = []
    lamp = Lamp.objects.get(id=lamp_id)
    l = model_to_dict(lamp, fields=[], exclude=[])
    l['object_type'] = 'lamp'
    result.append(l)

    return result


@json_view
def dim(request, lamp_id, value):
    """По одной лампе в формате запроса: ?9=50
    """
    request_user = request.user if request.user.is_authenticated() else None
    if int(value) <= 100 and int(value) >= 0:
        lamp = Lamp.objects.get(id=lamp_id, node__owner=request_user)
        node = lamp.node
        logger.info("Node: %s" % node)
        if node.host:
            action = "dim?%s=%s" % (lamp.pin, value)
            result = node.make_request(action)
        else:
            lamp.level = value
            lamp.save()

    return [model_to_dict(Lamp.objects.get(id=lamp_id), fields=[], exclude=[])]


@json_view
def switch_zone_by_lamps(request, zone_id, status):
    """Работа с зоной по одной лампе, пока ардуинка не поддерживает много параметров
    """
    request_user = request.user if request.user.is_authenticated() else None
    zone = Zone.objects.get(id=zone_id, owner=request_user)
    for lamp in zone.lamps.all():
        node = lamp.node
        logger.info("Node: %s" % node)
        if node.host:
            action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
            res = node.make_request(action)
            if res is False:
                lamp.on = None
                lamp.save()
        else:
            lamp.on = True if status == 'on' else False
            lamp.save()

    result = []
    for lamp in zone.lamps.all():
        l = model_to_dict(lamp, fields=[], exclude=[])
        l['object_type'] = 'lamp'
        result.append(l)

    return result



@json_view
def switch_all_by_lamps(request, status):
    request_user = request.user if request.user.is_authenticated() else None
    lamps = []
    result = []
    for node in Node.objects.filter(owner=request_user).all():
        for lamp in node.lamp_set.all():
            node = lamp.node
            logger.info("Node: %s" % node)
            if node.host:
                action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
                res = node.make_request(action)
                if res is None:
                    break
                elif res is False:
                    lamp.on = None
                    lamp.save()
            else:
                lamp.on = True if status == 'on' else False
                lamp.save()

        for lamp in node.lamp_set.all():
            l = model_to_dict(lamp, fields=[], exclude=[])
            l['object_type'] = 'lamp'
            result.append(l)

    return result


@json_view
def check(request):
    """depricated Запрос ардуинки на внеочередную проверку - нужно избавиться
    """
    request_user = request.user if request.user.is_authenticated() else None
    host = '192.168.1.222'
    logger.info("Check host: %s" % host)
    nodes = Node.objects.filter(host=host, owner=request_user).all()
    if nodes:
        node = nodes[0]
        logger.info("Check node: %s" % node)
        node.refresh_all()

    return {}


def parse_device_string(device_string):
    """Парсер строки GET запроса
    """
    logger.info("Request: %s" % device_string)
    device_list = []
    devices = device_string.split(',') if device_string else []
    for device in devices:
        values = device.split(':')
        if len(values) > 1:
            ids = values[0].split('!')
            logger.info("Values: %s, pin/sid: %s" % (len(values), ids))
            device_dict = {}
            device_dict['pin'] = int(ids[0])
            if len(ids) > 1:
                device_dict['sid'] = ids[1]
            else:
                device_dict['sid'] = None
            device_dict['on'] = values[1] != u'0' if values[1] != u'' else None
            if len(values) > 2 and values[2] != '':
                device_dict['level'] = None if values[2] == u'' else float(values[2])
            if len(values) > 3:
                device_dict['value'] = None if values[3] == u'' else float(values[3])
            device_list.append(device_dict)

    logger.info("Devices: %s" % device_list)
    return device_list


@render_string
def communicate(request, token):
    """Универсальный запрос ардуинки, присылает любую инфу и запрашивает статус
       Статус возвращает состояние сенсоров
       Порядок: ардуинка отправляет статус изменений, центр его применяет и отправляет статус ламп
       TODO получать в запросе состояние ардуинки
       data=1!2333232:1,2:0,3:0
       data=pin!sid:on:level:value,pin!sid:on:level:value
    """
    node = Node.objects.get(token=token)

    device_list = parse_device_string(request.GET.get('data'))
    node.apply_data(device_list, lazy=True)

    lamps = []
    result = []
    for lamp in node.lamp_set.all():
        on = {True: 1, False: 0}.get(lamp.on, '')
        lamps.append({
            'pin': lamp.pin,
            'on': on,
            'level': lamp.level if lamp.dimmable else ''
            })
        result.append({
            'node': node.id,
            'pin': lamp.pin,
            'on': lamp.on,
            'object_type': 'lamp',
            'id': lamp.id,
            'level': lamp.level if lamp.dimmable else ''
            })

    r = redis.StrictRedis()

    channel = 'node_%d_messages' % node.id
    for sensor in node.sensor_set.all():
        result.append({
            'node': node.id,
            'pin': sensor.pin,
            'object_type': 'sensor',
            'id': sensor.id,
            'value': sensor.value
            })


    r.publish(channel, json.dumps({
        "env": "ecc",
        "user_id": node.owner_id,
        "node_id": node.id,
        "data": json.dumps(result),
    }))

    return lamps


@render_string
def post(request, token):
    """Запрос от ардуинки, присылает любую инфу
       Порядок: ардуинка отправляет статус изменений, центр его применяет
       Система применяет изменения только запрошенных пинов, остальные не трогаются
       data=1!2333232:1,2:0,3:0
       data=pin!sid:on:level:value,pin!sid:on:level:value
    """
    node = Node.objects.get(token=token)

    device_list = parse_device_string(request.GET.get('data'))
    node.apply_data(device_list, lazy=True)

    return []

@render_string
def get(request, token):
    """Запрос от ардуинки, запрашивает информацию состояний, в которые ей нужно выставить исполнительные устройства
       Не получает информацию о датчиках, если они ей не нужны
       Порядок: ардуинка отправляет статус изменений, центр его применяет
       data=1!2333232:1,2:0,3:0
       data=pin!sid:on:level:value,pin!sid:on:level:value
    """
    node = Node.objects.get(token=token)

    lamps = []
    for lamp in node.lamp_set.all():
        on = {True: 1, False: 0}.get(lamp.on, '')
        lamps.append({
            'pin': lamp.pin,
            'on': on,
            'level': lamp.level if lamp.dimmable else ''
            })

    return lamps


@json_view
def get_sensor_data_for_morris(request, sensor_id):
    request_user = request.user if request.user.is_authenticated() else None
    sensor = Sensor.objects.get(id=sensor_id, node__owner=request_user)
    truncate_date = connection.ops.date_trunc_sql('hour', 'time')
    qs = sensor.sensorhistory_set.extra({'hour':truncate_date})
    report = qs.filter(time__gte=timezone.now() - timedelta(hours=24), time__lt=timezone.now()).values('hour').annotate(Avg('value'), Min('value'), Max('value'), Count('id')).order_by('hour')

    result = []
    try:
        for item in report:
            logger.info("Item: %s" % item)

            result.append({
                'time': item['hour'].strftime("%Y-%m-%d %H:00:00%z"),
                'avg': "{:.1f}".format(item['value__avg']),
                'min': "{:.1f}".format(item['value__min']),
                'max': "{:.1f}".format(item['value__max']),
                'count': int(item['id__count'])
            });
    except TypeError: # Скрываем пустые результаты
        return []

    return result


@json_view
def inventory_status(request):
    request_user = request.user if request.user.is_authenticated() else None
    req = request.GET.lists()
    logger.debug("req: %s" % req)
    result = []
    for group in req:
        logger.debug("group: %s" % group[0])
        if group[0] == 'lamp_id':
            for lamp_id in group[1]:
                lamp = Lamp.objects.get(id=lamp_id, node__owner=request_user)
                l = model_to_dict(lamp, fields=[], exclude=[])
                l['object_type'] = 'lamp'
                result.append(l)

        if group[0] == 'sensor_id':
            for sensor_id in group[1]:
                sensor = Sensor.objects.get(id=sensor_id, node__owner=request_user)
                l = model_to_dict(sensor, fields=[], exclude=[])
                l['object_type'] = 'sensor'
                result.append(l)


    return result
