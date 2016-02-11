#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible  # only if you need to support Python 2
class Pin(models.Model):
    """
    """
    on = models.NullBooleanField(default=None, null=True)
    pin = models.IntegerField(default=None)
    node = models.IntegerField(default=0)

    def __str__(self):
        return "%s (%s): %s" % (self.pin, self.node, self.on)

    class Meta:
        ordering = ('node', 'pin',)
        unique_together = ('node', 'pin',)

