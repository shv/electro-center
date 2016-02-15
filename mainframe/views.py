#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import httplib, urllib
import json

from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.template import loader
from django.utils import timezone
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview

from .models import Node, Lamp, Zone

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


# TODO: Перенести в модель
def update_node(node):
    """ Сбор данных с ардуинок
        Вынести в отдельную периодическую таску
    """
    logger.info("Node: %s" % node)
    try:
        conn = httplib.HTTPConnection(node.host, timeout=REQUEST_TIMEOUT)
        conn.request("GET", "/status")
        response = conn.getresponse()
    except:
        return

    if response.status == 200:
        data = json.loads(response.read())
        conn.close()
        logger.info(data)
        data_dict = {d["pin"]:d for d in data}
        logger.info(data_dict)
        for lamp in node.lamp_set.all():
            lamp.on = data_dict[lamp.pin]["on"] if lamp.pin in data_dict else None
            logger.info("%s: %s" % (lamp.pin, lamp.on))
            lamp.save()
        for sensor in node.sensor_set.all():
            sensor.value = data_dict[sensor.pin]["value"] if sensor.pin in data_dict else None
            sensor.time = timezone.now()
            logger.info("%s: %s" % (sensor.pin, sensor.value))
            sensor.save()
            sensor.sensorhistory_set.create(value=sensor.value, node=sensor.node, pin=sensor.pin, time=sensor.time, type=sensor.type)
        node.last_answer_time = timezone.now()
        node.save()

@render
def index(request):
    return dict(
        template = 'mainframe/index.html'
    )


@render
def zone(request, zone_id):
    zone = Zone.objects.get(id=zone_id)
    for node in zone.nodes():
        update_node(node)

    return dict(
        template = 'mainframe/zone.html',
        zone = zone
    )


@render
def node(request, node_id):
    node = Node.objects.get(id=node_id)
    update_node(node)
    return dict(
        template = 'mainframe/node.html',
        active_menu = 'nodes',
        node = node
    )


@json_view
def lamps(request, node_id):
    node = Node.objects.get(id=node_id)
    update_node(node)

    return [model_to_dict(lamp, fields=[], exclude=[]) for lamp in node.lamp_set.all()]


@json_view
def switch(request, lamp_id, status):
    """По одной лампе в формате запроса: ?9=true
    """
    lamp = Lamp.objects.get(id=lamp_id)
    node = lamp.node
    logger.info("Node: %s" % node)
    try:
        conn = httplib.HTTPConnection(node.host, timeout=REQUEST_TIMEOUT)
        conn.request("GET", "/switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false'))
        response = conn.getresponse()
    except:
        return [model_to_dict(Lamp.objects.get(id=lamp_id), fields=[], exclude=[])]

    if response.status == 200:
        data = json.loads(response.read())
        conn.close()
        logger.info(data)
        data_dict = {d["pin"]:d for d in data}
        logger.info(data_dict)
        for lamp_ in node.lamp_set.all():
            lamp_.on = data_dict[lamp_.pin]["on"] if lamp_.pin in data_dict else None
            logger.info("%s: %s" % (lamp_.pin, lamp_.on))
            lamp_.save()
        node.last_answer_time = timezone.now()
        node.save()

    else:
        lamp.on = None
        logger.info("%s: %s" % (lamp.pin, lamp.on))
        lamp.save()

    return [model_to_dict(Lamp.objects.get(id=lamp_id), fields=[], exclude=[])]


@json_view
def switch_zone_by_lamps(request, zone_id, status):
    """Работа с зоной по одной лампе, пока ардуинка не поддерживает много параметров
    """
    zone = Zone.objects.get(id=zone_id)
    for lamp in zone.lamps.all():
        node = lamp.node
        logger.info("Node: %s" % node)
        try:
            conn = httplib.HTTPConnection(node.host, timeout=REQUEST_TIMEOUT)
            conn.request("GET", "/switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false'))
            response = conn.getresponse()
        except:
            continue

        if response.status == 200:
            data = json.loads(response.read())
            conn.close()
            logger.info(data)
            data_dict = {d["pin"]:d for d in data}
            logger.info(data_dict)
            for lamp_ in node.lamp_set.all():
                lamp_.on = data_dict[lamp_.pin]["on"] if lamp_.pin in data_dict else None
                logger.info("%s: %s" % (lamp_.pin, lamp_.on))
                lamp_.save()

            node.last_answer_time = timezone.now()
            node.save()

        else:
            for lamp_ in node.lamp_set.all():
                lamp_.on = None
                lamp_.save()

    return [model_to_dict(lamp, fields=[], exclude=[]) for lamp in zone.lamps.all()]



@json_view
def switch_all_by_lamps(request, status):
    lamps = []
    for node in Node.objects.all():
        for lamp in node.lamp_set.all():
            node = lamp.node
            logger.info("Node: %s" % node)
            try:
                conn = httplib.HTTPConnection(node.host, timeout=REQUEST_TIMEOUT)
                conn.request("GET", "/switch?%s=%s" % (lamp.pin, 'true' if status == 'on' else 'false'))
                response = conn.getresponse()
            except:
                break

            if response.status == 200:
                data = json.loads(response.read())
                conn.close()
                logger.info(data)
                data_dict = {d["pin"]:d for d in data}
                logger.info(data_dict)
                for lamp_ in node.lamp_set.all():
                    lamp_.on = data_dict[lamp_.pin]["on"] if lamp_.pin in data_dict else None
                    logger.info("%s: %s" % (lamp_.pin, lamp_.on))
                    lamp_.save()

                node.last_answer_time = timezone.now()
                node.save()

            else:
                for lamp_ in node.lamp_set.all():
                    lamp_.on = None
                    lamp_.save()


        lamps.extend([model_to_dict(lamp, fields=[], exclude=[]) for lamp in node.lamp_set.all()])

    return lamps
