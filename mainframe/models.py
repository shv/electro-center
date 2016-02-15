#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible  # only if you need to support Python 2
class Node(models.Model):
    """Arduins
    """
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    last_answer_time = models.DateTimeField('last answer time')

    def __str__(self):
        return "%s (%s)" % (self.name, self.host)

    class Meta:
        ordering = ('name',)


@python_2_unicode_compatible  # only if you need to support Python 2
class Lamp(models.Model):
    """
    """
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    on = models.NullBooleanField(default=None)
    pin = models.IntegerField(default=None, null=True)

    def __str__(self):
        return "%s (%s): %s" % (self.name, self.node, self.on)

    class Meta:
        ordering = ('name',)
        unique_together = ('node', 'pin',)


@python_2_unicode_compatible  # only if you need to support Python 2
class SensorType (models.Model):
    """Типы датчиков
       (датчики света, температуры, влажности...)
    """
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return "%s" % (self.name)

    class Meta:
        ordering = ('name',)


@python_2_unicode_compatible  # only if you need to support Python 2
class Sensor (models.Model):
    """Набор сенсоров, значения которых изменяются со временем
       (датчики света, температуры, влажности...)
    """
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    type = models.ForeignKey(SensorType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    value = models.IntegerField(default=None, null=True)
    pin = models.IntegerField(default=None, null=True)
    time = models.DateTimeField('Last value time')

    def __str__(self):
        return "%s (%s) on %s: %s [%s]" % (self.name, self.type, self.node, self.value, self.time)

    class Meta:
        ordering = ('name',)
        unique_together = ('node', 'pin',)


@python_2_unicode_compatible  # only if you need to support Python 2
class SensorHistory (models.Model):
    """История значений сенсоров
    """
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    value = models.IntegerField(default=None, null=True)
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, default=None, null=True)
    pin = models.IntegerField(default=None, null=True)
    time = models.DateTimeField('Value at time')
    type = models.ForeignKey(SensorType, on_delete=models.SET_NULL, default=None, null=True)

    def __str__(self):
        return "[%s]: %s on %s [%s]" % (self.time, self.value, self.node, self.pin)

    class Meta:
        ordering = ('time', 'node')


@python_2_unicode_compatible  # only if you need to support Python 2
class Zone(models.Model):
    """Зоны расположения ламп
    """
    name = models.CharField(max_length=255)
    lamps = models.ManyToManyField(Lamp)
    sensors = models.ManyToManyField(Sensor)

    def __str__(self):
        return "%s" % self.name

    def nodes(self):
        nodes = {}
        for lamp in self.lamps.all():
            node = lamp.node
            nodes[node.id] = node
        return nodes.values()

    class Meta:
        ordering = ('name',)

    # owner = models.ForeignKey(User)

    # def __str__(self):

    #     return ' '.join([
    #         self.first_name,
    #         self.last_name,
    #     ])
