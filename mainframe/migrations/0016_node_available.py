# -*- coding: utf-8 -*-
# Generated by Django 1.11.dev20160614132808 on 2016-06-16 16:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainframe', '0015_auto_20160616_1434'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='available',
            field=models.BooleanField(default=False),
        ),
    ]
