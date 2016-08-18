# -*- coding: utf-8 -*-
import logging
from django.db import connection
from time import time
from operator import add
from django.forms.models import model_to_dict

from mainframe.models import Lamp, Zone, Node

logger = logging.getLogger(__name__)


def parse_device_string(device_string):
    """Парсер строки GET запроса для одной ноды
    """
    device_list = []
    logger.debug(device_string)
    devices = device_string.split(';') if device_string else []
    for device in devices:
        values = device.split(':')
        if len(values) > 1:
            device_type = values[0]
            device_dict = {}
            if len(values) > 1:
                device_dict['external_id'] = values[1]
            if device_type == u'l':
                device_dict['object_type'] = 'lamp'
                device_dict['on'] = {u'1': True, u'0': False}.get(values[2])
                logger.debug("Value {}, on: {}".format(values[1], device_dict['on']))
                if len(values) > 3:
                    device_dict['auto'] = {u'1': True, u'0': False}.get(values[3])
                else:
                    device_dict['auto'] = None
                if len(values) > 4 and values[4] != '':
                    device_dict['level'] = None if values[4] == u'' else float(values[4])
                else:
                    device_dict['level'] = None
            elif device_type == u's':
                device_dict['object_type'] = 'sensor'
                if len(values) > 2:
                    device_dict['value'] = None if values[2] == u'' else float(values[2])
                else:
                    device_dict['value'] = None
            device_list.append(device_dict)

    return device_list

def generate_device_string(data_list):
    """l:id:on:auto:level,s:id:value
    """
    result = []
    for device in data_list:
        if device['object_type'] == 'lamp':
            result.append("l:{}:{}:{}:{}".format(device['external_id'], {True: '1', False: '0'}.get(device.get('on'), ''), {True: '1', False: '0'}.get(device.get('auto'), ''), device.get('level', '')))
        elif device['object_type'] == 'sensor':
            result.append("s:{}:{}".format(device['external_id'], device.get('value', '')))

    return ';'.join(result)

"""
    Формат строки на:
    <type>:<id>:<state>;<type>:<id>:<state>
    type: типы устройств, сейчас:
      s - сенсор
      l - лампа
    id: внутренний id устройства уникальный для ардуинки (строка). Можно генерировать как pin_sid
    В базу добавляем к сенсорам и лампам external_id. По нему же должен работать ECC.

    state: значения разные для разных типов
      s: значение сенсора
      l: строка из двух значений "<on>:<auto>:<level>"
        on: 1 - включена, 0 - выключена, '' - неопределено
        auto: 1 - включена, 0 - выключена, '' - неопределено
        level: уровень диммера
"""

def stats_decorator(f):
    def tmp(*args, **kwargs):
        # get number of db queries before we do anything
        n = len(connection.queries)

        # time the view
        start = time()

        context = f(*args, **kwargs)
        total_time = time() - start

        # compute the db time for the queries just run
        db_queries = len(connection.queries) - n
        if db_queries:
            db_time = reduce(add, [float(q['time'])
                                   for q in connection.queries[n:]])
        else:
            db_time = 0.0

        logger.debug("TIME for «{}». Total: {:.5f} sec, DB ({}): {} sec".format(f.__name__, total_time, db_queries, db_time))

        return context

    return tmp

