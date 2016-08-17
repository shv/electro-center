#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import httplib, urllib
import json
import redis #pip install redis

from django.forms.models import model_to_dict
from django.conf import settings
from django.db.models import Sum, Count, Avg, Min, Max
from django.http import HttpResponse
from django.db import connection
from django.template import loader
from django.utils import timezone
from datetime import timedelta
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview
from django.views.decorators.csrf import csrf_exempt

from .models import Node, Lamp, Zone, Sensor
from mainframe.utils import parse_device_string, generate_device_string, stats_decorator

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
            nodes = Node.objects.filter(owner=request_user).all(),
            parent_template = context.get('parent_template'),
            active_menu = context.get('active_menu'),
            settings = settings,
        ))

        template = loader.get_template(context['template'])
        return HttpResponse(template.render(context, request))

    return tmp


def render_string(f):
    def tmp(request, *args, **kwargs):
        context = f(request, *args, **kwargs)
        logger.debug(context)
        result = generate_device_string(context)
        return HttpResponse(result)

    return tmp


@stats_decorator
@render
def index(request):
    """ Генерация главной страницы
    """
    request_user = request.user if request.user.is_authenticated() else None
    sensors = Sensor.objects.filter(node__owner=request_user).all()
    return dict(
        template = 'mainframe/index.html',
        sensors = sensors
    )


@stats_decorator
@render
def zone(request, zone_id):
    """ Генерация страницы зоны
    """
    request_user = request.user if request.user.is_authenticated() else None
    zone = Zone.objects.get(id=zone_id, owner=request_user)
    for node in zone.nodes():
        if node.host:
            node.refresh_all()

    return dict(
        template = 'mainframe/zone.html',
        active_menu = 'zones',
        zone = zone
    )


@stats_decorator
@render
def node(request, node_id):
    """ Генерация страницы ноды
    """
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
    """ TODO нужно выкосить
    """
    request_user = request.user if request.user.is_authenticated() else None
    node = Node.objects.get(id=node_id, owner=request_user)
    if node.host:
        node.refresh_all()

    return [model_to_dict(lamp, fields=[], exclude=[]) for lamp in node.lamp_set.all()]


@json_view
def switch(request, lamp_id, status):
    """ TODO нужно выкосить
    """
    request_user = request.user if request.user.is_authenticated() else None
    lamp = Lamp.objects.get(id=lamp_id, node__owner=request_user)
    node = lamp.node
    logger.info("Node: %s" % node)
    if node.host:
        action = "switch?%s=%s" % (lamp.pin, str(status))
        result = node.make_request(action)

        if not result:
            lamp.on = None
            logger.info("%s: %s" % (lamp.pin, lamp.on))
            lamp.save()
    else:
        lamp.on = status
        lamp.save()


    result = []
    lamp = Lamp.objects.get(id=lamp_id)
    l = model_to_dict(lamp, fields=[], exclude=[])
    l['object_type'] = 'lamp'
    result.append(l)

    return result


@json_view
def dim(request, lamp_id, value):
    """ TODO нужно выкосить
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
    """ TODO нужно выкосить
    """
    request_user = request.user if request.user.is_authenticated() else None
    zone = Zone.objects.get(id=zone_id, owner=request_user)
    for lamp in zone.lamps.all():
        node = lamp.node
        logger.info("Node: %s" % node)
        if node.host:
            action = "switch?%s=%s" % (lamp.pin, 'true' if status else 'false')
            res = node.make_request(action)
            if res is False:
                lamp.on = None
                lamp.save()
        else:
            lamp.on = status
            lamp.save()

    result = []
    for lamp in zone.lamps.all():
        l = model_to_dict(lamp, fields=[], exclude=[])
        l['object_type'] = 'lamp'
        result.append(l)

    return result



@json_view
def switch_all_by_lamps(request, status):
    """ TODO нужно выкосить
    """
    request_user = request.user if request.user.is_authenticated() else None
    lamps = []
    result = []
    for node in Node.objects.filter(owner=request_user).all():
        for lamp in node.lamp_set.all():
            node = lamp.node
            logger.info("Node: %s" % node)
            if node.host:
                action = "switch?%s=%s" % (lamp.pin, 'true' if status else 'false')
                res = node.make_request(action)
                if res is None:
                    break
                elif res is False:
                    lamp.on = None
                    lamp.save()
            else:
                lamp.on = status
                lamp.save()

        for lamp in node.lamp_set.all():
            l = model_to_dict(lamp, fields=[], exclude=[])
            l['object_type'] = 'lamp'
            result.append(l)

    return result


@json_view
def check(request):
    """ TODO нужно выкосить
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


@render_string
def communicate(request, token):
    """TODO нужно выкосить после настройки сокетов
       Универсальный запрос ардуинки, присылает любую инфу и запрашивает статус
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
        lamps.append({
            'pin': lamp.pin,
            'on': lamp.on,
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
    """TODO нужно выкосить после настройки сокетов
       Запрос от ардуинки, присылает любую инфу
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
    """TODO нужно выкосить после настройки сокетов
       Запрос от ардуинки, запрашивает информацию состояний, в которые ей нужно выставить исполнительные устройства
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


@stats_decorator
@json_view
def get_sensor_data_for_morris(request, sensor_id):
    """ Оптимизировать
    """
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
    """ TODO нужно выкосить
    """
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


@csrf_exempt
@stats_decorator
@json_view
def api_sync(request):
    """ Внутренний запрос на асинхронное изменения
        Вызывается при запросе в сокет на изменение
        Не требует обычной авторизации, проверка только по API
        Должен быть закрыт из внешнего мира
    """
    api_key = request.POST.get("api_key")
    if api_key != settings.API_KEY:
        return {"error": "Please pass a correct API key."}
    node_id = request.POST.get("node_id")

    node = Node.objects.get(id=node_id)

    logger.debug(request.POST.get('data'))
    device_list = json.loads(request.POST.get('data'))
    logger.debug(device_list)

    node.apply_data(device_list, lazy=True)

    lamps = []
    result = []
    for lamp in node.lamp_set.all():
        result.append({
            'node': node.id,
            'external_id': lamp.external_id,
            'on': lamp.on,
            'auto': lamp.auto,
            'object_type': 'lamp',
            'id': lamp.id,
            'dimmable': lamp.dimmable,
            'level': lamp.level if lamp.dimmable else ''
            })

    for sensor in node.sensor_set.all():
        result.append({
            'node': node.id,
            'external_id': sensor.external_id,
            'object_type': 'sensor',
            'id': sensor.id,
            'value': sensor.value
            })

    logger.debug(result)
    #return json.dumps(result)
    return result

@csrf_exempt
@stats_decorator
@json_view
def ecc_sync(request):
    """ Внутренний запрос на асинхронное изменения
        Вызывается при запросе в сокет на изменение
        Не требует обычной авторизации, проверка только по API
        Должен быть закрыт из внешнего мира
    """
    api_key = request.POST.get("api_key")
    if api_key != settings.API_KEY:
        return {"error": "Please pass a correct API key."}
    user_id = request.POST.get("user_id")

    device_list = json.loads(request.POST.get('data'))
    logger.debug("device_list: %s" % device_list)
    device_ids_by_type = {'lamp': {}, 'sensor': {}, 'zone_lamps': {}, 'all_lamps': {}}
    for device in device_list:
        device_ids_by_type[device["object_type"]][device.get("id")] = device

    logger.debug("device_ids_by_type: %s" % device_ids_by_type)

    nodes = {}
    lamps = []
    sensors = []
    lamps_for_zone = {} # Дополнительные значения лам при переключении всей зоны
    if len(device_ids_by_type["lamp"].keys()):
        lamps = list(Lamp.objects.filter(id__in=device_ids_by_type["lamp"].keys()))

    if len(device_ids_by_type["zone_lamps"].keys()):
        # Единичная лампа имеет приоритет перед зоной
        for zone in Zone.objects.filter(id__in=device_ids_by_type["zone_lamps"].keys(), owner_id=user_id).all():
            for zone_lamp in zone.lamps.all():
                if zone_lamp.id not in device_ids_by_type["lamp"]:
                    lamps.append(zone_lamp)
                    lamps_for_zone[zone_lamp.id] = {"on": device_ids_by_type["zone_lamps"][zone.id]["on"]}

    if len(device_ids_by_type["all_lamps"].keys()):
        # Единичная лампа и зона имеет приоритет перед зоной
        for node in Node.objects.filter(owner_id=user_id):
            nodes[node.id] = node
        for node_lamp in Lamp.objects.filter(node_id__in=nodes.keys()):
            if node_lamp.id not in device_ids_by_type["lamp"] and node_lamp.id not in lamps_for_zone:
                lamps.append(node_lamp)
                lamps_for_zone[node_lamp.id] = {"on": device_ids_by_type["all_lamps"][None]["on"]}

    if len(device_ids_by_type["sensor"].keys()):
        sensors = Sensor.objects.filter(id__in=device_ids_by_type["sensor"].keys())


    logger.debug("lamps: %s" % lamps)
    logger.debug("sensors: %s" % sensors)
    logger.debug("lamps_for_zone: %s" % lamps_for_zone)

    for lamp in lamps:
        if lamp.node_id not in nodes:
            nodes[lamp.node_id] = Node.objects.get(id=lamp.node_id, owner_id=user_id)

        # Сначала проверяем единичные лампы, затем зону
        lamp_ = device_ids_by_type["lamp"].get(lamp.id, lamps_for_zone.get(lamp.id))
        if lamp_.get("on") is not None:
            lamp.on = lamp_["on"]
        if lamp_.get("auto") is not None:
            lamp.auto = lamp_["auto"]
        if lamp_.get("level") is not None:
            lamp.level = lamp_["level"]
        lamp.save()


    for sensor in sensors:
        if sensor.node_id not in nodes:
            nodes[sensor.node_id] = Node.objects.get(id=sensor.node_id, owner_id=user_id)
            # TODO

    result = {}
    for lamp in lamps:
        if lamp.node_id not in result:
            result[lamp.node_id] = []

        result[lamp.node_id].append({
            'node': lamp.node_id,
            'pin': lamp.pin,
            'on': lamp.on,
            'auto': lamp.auto,
            'object_type': 'lamp',
            'id': lamp.id,
            'external_id': lamp.external_id,
            'dimmable': lamp.dimmable,
            'level': lamp.level if lamp.dimmable else ''
            })

    for sensor in sensors:
        if sensor.node_id not in result:
            result[sensor.node_id] = []

        result.append({
            'node': sensor.node_id,
            'pin': sensor.pin,
            'object_type': 'sensor',
            'id': sensor.id,
            'external_id': lamp.external_id,
            'value': sensor.value
            })
    return result
