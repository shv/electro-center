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
    last_answer_time = models.DateTimeField('last answer time', blank=True, null=True)
    # Владелец ноды, который ее создал, может редактировать и удалять, а так же менять состав
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    token = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, blank=True)
    online = models.BooleanField(default=False)
    pinging = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % (self.name)

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
    dimmable = models.BooleanField(default=False)
    level = models.IntegerField(default=0)

    def __str__(self):
        return "%s (%s), ID: %s" % (self.name, self.node_id, self.external_id)

    class Meta:
        ordering = ('id',)
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
    time = models.DateTimeField('Last value time', blank=True, null=True)

    def __str__(self):
        return "%s (%s), ID: %s" % (self.name, self.node_id, self.external_id)

    def save(self, *args, **kwargs):
        if self.value == u'':
            self.value = None
        super(Sensor, self).save(*args, **kwargs)

    class Meta:
        ordering = ('name',)
        unique_together = ('node', 'external_id')


@python_2_unicode_compatible  # only if you need to support Python 2
class SensorHistory (models.Model):
    """История значений сенсоров
    """
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=31, db_index=True, null=True)
    value = models.FloatField(default=None, null=True, blank=True)
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, default=None, null=True)
    time = models.DateTimeField('Value at time', db_index=True, blank=True, null=True)
    type = models.ForeignKey(SensorType, on_delete=models.SET_NULL, default=None, null=True)

    def __str__(self):
        return "[%s] %s, ID: %s" % (self.node_id, self.sensor_id, self.external_id)

    def save(self, *args, **kwargs):
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
