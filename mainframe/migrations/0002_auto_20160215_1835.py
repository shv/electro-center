# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-15 15:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mainframe', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sensor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('value', models.IntegerField(default=None)),
                ('pin', models.IntegerField(default=None, null=True)),
                ('time', models.DateTimeField(verbose_name='Last value time')),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainframe.Node')),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='SensorHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(default=None)),
                ('pin', models.IntegerField(default=None, null=True)),
                ('time', models.DateTimeField(verbose_name='Value at time')),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainframe.Node')),
            ],
            options={
                'ordering': ('time', 'node'),
            },
        ),
        migrations.CreateModel(
            name='SensorType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.AddField(
            model_name='sensorhistory',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainframe.SensorType'),
        ),
        migrations.AddField(
            model_name='sensor',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainframe.SensorType'),
        ),
        migrations.AddField(
            model_name='zone',
            name='sensors',
            field=models.ManyToManyField(to='mainframe.Sensor'),
        ),
    ]
