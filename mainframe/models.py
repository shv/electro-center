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


@python_2_unicode_compatible  # only if you need to support Python 2
class Zone(models.Model):
    """Зоны расположения ламп
    """
    name = models.CharField(max_length=255)
    lamps = models.ManyToManyField(Lamp)

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