# -*- coding: utf-8 -*-
# Generated by Django 1.11.dev20160614132808 on 2016-06-16 11:17
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainframe', '0012_auto_20160616_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='zone',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]