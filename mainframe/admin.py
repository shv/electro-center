from django.contrib import admin

from .models import Node, Lamp, Zone, Sensor, SensorType, SensorHistory

admin.site.register(Node)
admin.site.register(Lamp)
admin.site.register(Zone)
admin.site.register(Sensor)
admin.site.register(SensorType)
admin.site.register(SensorHistory)
