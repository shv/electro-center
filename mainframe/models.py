#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import httplib, urllib
import json
import logging
import uuid


from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

logger = logging.getLogger(__name__)


REQUEST_TIMEOUT = 1


@python_2_unicode_compatible  # only if you need to support Python 2
class Node(models.Model):
    """Arduins
    """
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255, blank=True, null=True) # Если NULL то пассивный режим
    last_answer_time = models.DateTimeField('last answer time', blank=True, null=True)
    # Владелец ноды, который ее создал, может редактировать и удалять, а так же менять состав
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    token = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, blank=True)

    def __str__(self):
        return "%s" % (self.name)


    def make_request(self, action, lamp=None):
        if self.host is None or not self.host:
            # Если нода недоступна для опроса, то даже не пытаемся
            return False

        try:
            conn = httplib.HTTPConnection(self.host, timeout=REQUEST_TIMEOUT)
            conn.connect()
            conn.putrequest("GET", "/%s" % action, True, True)
            conn.endheaders()
            response = conn.getresponse()
        except:
            logger.exception("Request exception")
            for lamp_ in self.lamp_set.all():
                lamp_.on = None
                lamp_.save()

            return None

        if response.status == 200:
            data = json.loads(response.read())
            conn.close()
            return self.apply_data(data)

        else:
            return False


    def apply_data(self, data, lazy=False):
        logger.info("data: %s" % data)
        data_dict = {}
        for d in data:
            data_dict[d["external_id"]] = d
        logger.info("data_dict: %s" % data_dict)
        for lamp in self.lamp_set.all():
            if lamp.external_id in data_dict:
                lamp.on = data_dict[lamp.external_id]["on"]
                lamp.auto = data_dict[lamp.external_id]["auto"]
                level = data_dict[lamp.external_id].get("level")
                lamp.level = level if level is not None else 0
                logger.info("lamp.level: %s" % lamp.level)
                # Автоматически проставляем возможность диммирования лампы
                lamp.dimmable = True if data_dict[lamp.external_id].get("level") is not None else False
                logger.info("%s: %s" % (lamp.pin, lamp.on))
                lamp.save()

        # Значения сенсоров нужно применять не чаще чем раз в 5 секунд
        for sensor in self.sensor_set.all():
            if sensor.external_id in data_dict:
                time_now = timezone.now()
                # Период обновления должен зависеть от того, облако это или нет
                # Есть смысл вообще сравнивать с предыдущим значением
                if sensor.sensorhistory_set.filter(time__gt=time_now-timezone.timedelta(seconds=5)):
                    logger.debug("Skip...")
                    continue

                logger.debug("Update...")


                sensor.value = data_dict[sensor.external_id]["value"]
                sensor.time = time_now
                sensor.save()
                sensor.sensorhistory_set.create(
                                                value=sensor.value,
                                                node=sensor.node,
                                                pin=sensor.pin,
                                                time=sensor.time,
                                                type=sensor.type,
                                                sid=sensor.sid,
                                                external_id=sensor.external_id
                                                )

        self.last_answer_time = timezone.now()
        self.save()

        return True



    def refresh_all(self):
        """ Сбор данных с ардуинок
        """
        return self.make_request('status')


    class Meta:
        ordering = ('name',)


@python_2_unicode_compatible  # only if you need to support Python 2
class Lamp(models.Model):
    """
    """
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=31, db_index=True, null=True)
    name = models.CharField(max_length=255)
    on = models.NullBooleanField(default=None)
    auto = models.NullBooleanField(default=None)
    # TODO удалить
    pin = models.IntegerField(default=None, null=True)
    dimmable = models.BooleanField(default=False)
    level = models.IntegerField(default=0)

    def __str__(self):
        return "%s (%s), ID: %s" % (self.name, self.node_id, self.external_id)

    class Meta:
        ordering = ('id',)
        unique_together = ('node', 'pin',)
        unique_together = ('node', 'external_id',)


@python_2_unicode_compatible  # only if you need to support Python 2
class SensorType (models.Model):
    """Типы датчиков
       (датчики света, температуры, влажности...)
    """
    name = models.CharField(max_length=255)
    # Владелец типа сенсора, который ее создал, может редактировать и удалять, а так же менять состав
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "%s" % (self.name)

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'owner',)


@python_2_unicode_compatible  # only if you need to support Python 2
class Sensor (models.Model):
    """Набор сенсоров, значения которых изменяются со временем
       (датчики света, температуры, влажности...)
    """
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=31, db_index=True, null=True)
    type = models.ForeignKey(SensorType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    value = models.FloatField(default=None, null=True, blank=True)
    # TODO удалить
    pin = models.IntegerField(default=None, null=True)
    # TODO удалить
    sid = models.CharField(max_length=255, default=None, null=True, blank=True) # Sensor id
    time = models.DateTimeField('Last value time', blank=True, null=True)

    def __str__(self):
        return "%s (%s), ID: %s" % (self.name, self.node, self.external_id)

    def save(self, *args, **kwargs):
        if self.sid == u'':
            self.sid = None
        if self.value == u'':
            self.value = None
        super(Sensor, self).save(*args, **kwargs)

    class Meta:
        ordering = ('name',)
        unique_together = ('node', 'pin', 'sid')
        unique_together = ('node', 'external_id')


@python_2_unicode_compatible  # only if you need to support Python 2
class SensorHistory (models.Model):
    """История значений сенсоров
    """
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=31, db_index=True, null=True)
    value = models.FloatField(default=None, null=True, blank=True)
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, default=None, null=True)
    # TODO удалить
    pin = models.IntegerField(default=None, null=True)
    # TODO удалить
    sid = models.CharField(max_length=255, default=None, null=True, blank=True)
    time = models.DateTimeField('Value at time', db_index=True, blank=True, null=True)
    type = models.ForeignKey(SensorType, on_delete=models.SET_NULL, default=None, null=True)

    def __str__(self):
        return "[%s] %s, ID: %s" % (self.node_id, self.sensor_id, self.external_id)

    def save(self, *args, **kwargs):
        if self.sid == u'':
            self.sid = None
        if self.value == u'':
            self.value = None
        super(SensorHistory, self).save(*args, **kwargs)

    class Meta:
        index_together = ["sensor", "time"]
        ordering = ('time',)


@python_2_unicode_compatible  # only if you need to support Python 2
class Zone(models.Model):
    """Зоны расположения ламп
    """
    name = models.CharField(max_length=255)
    lamps = models.ManyToManyField(Lamp, blank=True)
    sensors = models.ManyToManyField(Sensor, blank=True)
    # Владелец зоны, который ее создал, может редактировать и удалять, а так же менять состав
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "%s" % (self.name)

    def nodes(self):
        nodes = {}
        for lamp in self.lamps.all():
            node = lamp.node
            nodes[node.id] = node
        return nodes.values()

    class Meta:
        ordering = ('name',)

    # def __str__(self):

    #     return ' '.join([
    #         self.first_name,
    #         self.last_name,
    #     ])
