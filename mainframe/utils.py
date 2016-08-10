# -*- coding: utf-8 -*-
from django.forms.models import model_to_dict

from mainframe.models import Lamp, Zone, Node

def switch(user, lamp_id, status, level):
    """По одной лампе в формате запроса: ?9=true
    """
    lamp = Lamp.objects.get(id=lamp_id, node__owner=user)
    node = lamp.node
    if level is not None and int(level) <= 100 and int(level) >= 0:
        lamp.level = level

    print "!!!!!"
    print status
    if status is not None:
        lamp.on = status

    lamp.save()

    result = {node.id: []}
    lamp = Lamp.objects.get(id=lamp_id)
    l = model_to_dict(lamp, fields=[], exclude=[])
    l['object_type'] = 'lamp'
    result[node.id].append(l)

    return result

def switch_zone_by_lamps(user, zone_id, status):
    """Работа с зоной по одной лампе, пока ардуинка не поддерживает много параметров
       TODO отпралять в разные очереди редиса
    """

    zone = Zone.objects.get(id=zone_id, owner=user)
    for lamp in zone.lamps.all():
        node = lamp.node
        lamp.on = status
        lamp.save()

    result = {}
    for lamp in zone.lamps.all():
        l = model_to_dict(lamp, fields=[], exclude=[])
        l['object_type'] = 'lamp'
        if lamp.node_id not in result:
            result[lamp.node_id] = []
        result[lamp.node_id].append(l)

    return result


def switch_all_by_lamps(user, status):
    result = {}
    for node in Node.objects.filter(owner=user).all():
        for lamp in node.lamp_set.all():
            node = lamp.node
            lamp.on = status
            lamp.save()

        for lamp in node.lamp_set.all():
            l = model_to_dict(lamp, fields=[], exclude=[])
            l['object_type'] = 'lamp'
            if lamp.node_id not in result:
                result[lamp.node_id] = []
            result[lamp.node_id].append(l)

    return result

def parse_device_string(device_string):
    """Парсер строки GET запроса
    """
    device_list = []
    devices = device_string.split(',') if device_string else []
    for device in devices:
        values = device.split(':')
        if len(values) > 1:
            ids = values[0].split('!')
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

    return device_list

def generate_device_string(data_list):
    result = []
    print "!!!"
    print data_list
    for pin in data_list:
        result.append("{:d}:{}:{}:{}".format(pin['pin'], {True: '1', False: '0'}.get(pin.get('on'), ''), pin.get('level', ''), pin.get('value', '')))

    return ','.join(result)
