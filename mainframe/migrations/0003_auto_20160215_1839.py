# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-15 15:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainframe', '0002_auto_20160215_1835'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensortype',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='lamp',
            unique_together=set([('node', 'pin')]),
        ),
        migrations.AlterUniqueTogether(
            name='sensor',
            unique_together=set([('node', 'pin')]),
        ),
    ]
