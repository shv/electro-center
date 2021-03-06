# -*- coding: utf-8 -*-
# Generated by Django 1.11.dev20160614132808 on 2016-06-16 10:09
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainframe', '0011_auto_20160413_1542'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='sensor',
            name='value',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='sensorhistory',
            name='value',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='zone',
            name='lamps',
            field=models.ManyToManyField(blank=True, to='mainframe.Lamp'),
        ),
        migrations.AlterField(
            model_name='zone',
            name='sensors',
            field=models.ManyToManyField(blank=True, to='mainframe.Sensor'),
        ),
    ]
