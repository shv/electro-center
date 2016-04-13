#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import httplib, urllib
import json

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


def render(f):
    def tmp(request, *args, **kwargs):
        context = f(request, *args, **kwargs)
        context.update(dict(
            zones = Zone.objects.all(),
            nodes = Node.objects.all()
        ))
        template = loader.get_template(context['template'])
        return HttpResponse(template.render(context, request))

    return tmp


@render
def index(request):
    return dict(
        template = 'mainframe/index.html',
        sensors = Sensor.objects.all()
    )


@render
def zone(request, zone_id):
    zone = Zone.objects.get(id=zone_id)
    for node in zone.nodes():
        node.refresh_all()

    return dict(
        template = 'mainframe/zone.html',
        zone = zone
    )


@render
def node(request, node_id):
    node = Node.objects.get(id=node_id)
    node.refresh_all()
    return dict(
        template = 'mainframe/node.html',
        active_menu = 'nodes',
        node = node
    )


@json_view
def lamps(request, node_id):
    node = Node.objects.get(id=node_id)
    node.refresh_all()

    return [model_to_dict(lamp, fields=[], exclude=[]) for lamp in node.lamp_set.all()]


@json_view
def switch(request, lamp_id, status):
    """По одной лампе в формате запроса: ?9=true
    """
    lamp = Lamp.objects.get(id=lamp_id)
    node = lamp.node
    logger.info("Node: %s" % node)
    action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
    result = node.make_request(action)

    if not result:
        lamp.on = None
        logger.info("%s: %s" % (lamp.pin, lamp.on))
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
    if int(value) <= 100 and int(value) >= 0:
        lamp = Lamp.objects.get(id=lamp_id)
        node = lamp.node
        logger.info("Node: %s" % node)
        action = "dim?%s=%s" % (lamp.pin, value)
        result = node.make_request(action)

    return [model_to_dict(Lamp.objects.get(id=lamp_id), fields=[], exclude=[])]


@json_view
def switch_zone_by_lamps(request, zone_id, status):
    """Работа с зоной по одной лампе, пока ардуинка не поддерживает много параметров
    """
    zone = Zone.objects.get(id=zone_id)
    for lamp in zone.lamps.all():
        node = lamp.node
        logger.info("Node: %s" % node)
        action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
        res = node.make_request(action)
        if res is False:
            lamp.on = None
            lamp.save()

    result = []
    for lamp in zone.lamps.all():
        l = model_to_dict(lamp, fields=[], exclude=[])
        l['object_type'] = 'lamp'
        result.append(l)

    return result



@json_view
def switch_all_by_lamps(request, status):
    lamps = []
    result = []
    for node in Node.objects.all():
        for lamp in node.lamp_set.all():
            node = lamp.node
            logger.info("Node: %s" % node)
            action = "switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false')
            res = node.make_request(action)
            if res is None:
                break
            elif res is False:
                lamp.on = None
                lamp.save()

        for lamp in node.lamp_set.all():
            l = model_to_dict(lamp, fields=[], exclude=[])
            l['object_type'] = 'lamp'
            result.append(l)

    return result


@json_view
def check(request):
    """Запрос ардуинки на внеочередную проверку
    """
    host = '192.168.1.222'
    logger.info("Check host: %s" % host)
    nodes = Node.objects.filter(host=host).all()
    if nodes:
        node = nodes[0]
        logger.info("Check node: %s" % node)
        node.refresh_all()

    return {}


@json_view
def get_sensor_data_for_morris(request, sensor_id):
    sensor = Sensor.objects.get(id=sensor_id)
    truncate_date = connection.ops.date_trunc_sql('hour', 'time')
    qs = sensor.sensorhistory_set.extra({'hour':truncate_date})
    report = qs.filter(time__gte=timezone.now() - timedelta(hours=24), time__lt=timezone.now()).values('hour').annotate(Avg('value'), Min('value'), Max('value'), Count('id')).order_by('hour')

    result = []
    try:
        for item in report:
            result.append({
                'time': item['hour'].strftime("%Y-%m-%d %H:00:00%z"),
                'avg': int(item['value__avg']),
                'min': int(item['value__min']),
                'max': int(item['value__max']),
                'count': int(item['id__count'])
            });
    except TypeError: # Скрываем пустые результаты
        return []

    return result


@json_view
def inventory_status(request):
    req = request.GET.lists()
    logger.debug("req: %s" % req)
    result = []
    for group in req:
        logger.debug("group: %s" % group[0])
        if group[0] == 'lamp_id':
            for lamp_id in group[1]:
                lamp = Lamp.objects.get(id=lamp_id)
                l = model_to_dict(lamp, fields=[], exclude=[])
                l['object_type'] = 'lamp'
                result.append(l)

        if group[0] == 'sensor_id':
            for sensor_id in group[1]:
                sensor = Sensor.objects.get(id=sensor_id)
                l = model_to_dict(sensor, fields=[], exclude=[])
                l['object_type'] = 'sensor'
                result.append(l)


    return result
