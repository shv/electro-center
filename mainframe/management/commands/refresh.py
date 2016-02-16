#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from mainframe.models import Node
from datetime import timedelta
from django.utils import timezone
from time import sleep

REFRESH_DELAY=3 # seconds

# https://docs.djangoproject.com/en/dev/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'Run refresher data from all nodes'

    # def add_arguments(self, parser):
    #     parser.add_argument('node_id', nargs='+', type=int)

    def handle(self, *args, **options):
        while True:
            early_than = timezone.now() - timedelta(seconds=REFRESH_DELAY);
            for node in Node.objects.filter(last_answer_time__lt=early_than).all():
                node.refresh_all();
                self.stderr.write(self.style.SUCCESS("Node %s (%s) updated" % (node.id, node.name)))

            sleep(1)
