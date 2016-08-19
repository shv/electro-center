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

    return dict(
        template = 'mainframe/node.html',
        active_menu = 'nodes',
        node = node
    )


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
    device_external_ids_by_type = {'lamp': {}, 'sensor': {}}
    for device in device_list:
        device_external_ids_by_type[device["object_type"]][device.get("external_id")] = device

    logger.debug("device_external_ids_by_type: %s" % device_external_ids_by_type)

    lamps = []
    sensors = []
    if len(device_external_ids_by_type["lamp"].keys()):
        lamps = list(Lamp.objects.filter(
            external_id__in=device_external_ids_by_type["lamp"].keys(),
            node_id=node.id,
        ))

    if len(device_external_ids_by_type["sensor"].keys()):
        sensors = list(Sensor.objects.filter(
            external_id__in=device_external_ids_by_type["sensor"].keys(),
            node_id=node.id,
        ))

    logger.debug("lamps: %s" % lamps)
    logger.debug("sensors: %s" % sensors)

    result = []
    for lamp in lamps:
        if lamp.external_id in device_external_ids_by_type["lamp"]:
            new_lamp = device_external_ids_by_type["lamp"][lamp.external_id]
            lamp.on = new_lamp["on"]
            lamp.auto = new_lamp["auto"]
            level = new_lamp.get("level")
            lamp.level = level if level is not None else 0
            # Автоматически проставляем возможность диммирования лампы
            lamp.dimmable = True if new_lamp.get("level") is not None else False
            lamp.save()
            logger.debug("Saved Lamp: %s: %s (%s)" % (lamp.external_id, lamp.on, lamp.level))

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

    for sensor in sensors:
        if sensor.external_id in device_external_ids_by_type["sensor"]:
            time_now = timezone.now()
            # Период обновления должен зависеть от того, облако это или нет
            # Есть смысл вообще сравнивать с предыдущим значением

            sensor.value = device_external_ids_by_type["sensor"][sensor.external_id]["value"]
            sensor.time = time_now
            sensor.save()
            # Проверять изменилось ли
            last_sensor_history = list(sensor.sensorhistory_set.filter(time__gt=time_now-timezone.timedelta(seconds=5)).order_by('time'))
            # if sensor.sensorhistory_set.filter(time__gt=time_now-timezone.timedelta(seconds=5)):
            #     logger.debug("Skip...")
            #     continue

            # logger.debug("Update history...")
            sensor.sensorhistory_set.create(
                                            value=sensor.value,
                                            node_id=sensor.node_id,
                                            time=sensor.time,
                                            type_id=sensor.type_id,
                                            external_id=sensor.external_id
                                            )

        result.append({
            'node': node.id,
            'external_id': sensor.external_id,
            'object_type': 'sensor',
            'id': sensor.id,
            'value': sensor.value
            })

    node.last_answer_time = timezone.now()
    node.online = True
    node.save()

    result.append({
        'object_type': 'node',
        'id': node.id,
        'online': node.online,
        'last_answer_time': node.last_answer_time.isoformat(),
        })

    logger.debug(result)
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
            'object_type': 'sensor',
            'id': sensor.id,
            'external_id': lamp.external_id,
            'value': sensor.value
            })
    return result
