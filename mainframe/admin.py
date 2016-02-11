from django.contrib import admin

from .models import Node, Lamp, Zone

admin.site.register(Node)
admin.site.register(Lamp)
admin.site.register(Zone)
