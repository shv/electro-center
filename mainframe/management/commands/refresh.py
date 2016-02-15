#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from mainframe.models import Node
from mainframe.views import update_node # TODO: Перенести в модель
from datetime import timedelta
from django.utils import timezone

REFRESH_DELAY=3 # seconds

# https://docs.djangoproject.com/en/dev/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'Refresh data from all nodes'

    # def add_arguments(self, parser):
    #     parser.add_argument('node_id', nargs='+', type=int)

    def handle(self, *args, **options):
    #    for node_id in options['node_id']:
        while True:
            early_than = timezone.now() - timedelta(seconds=REFRESH_DELAY);
            for node in Node.objects.filter(last_answer_time__lt=early_than).all():
                # TODO: Перенести в модель
                update_node(node);
                self.stderr.write(self.style.SUCCESS("Node %s (%s) updated" % (node.id, node.name)))
