from django.contrib import admin

from .models import Node, Lamp, Zone, Sensor, SensorType, SensorHistory

class NodeAdmin(admin.ModelAdmin):
    readonly_fields = ('token',)
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []
        if not request.user.is_superuser:
            # Exclude owner fields for non superuser
            self.exclude.append('owner')

        return super(NodeAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if not change:
                obj.owner = request.user
        obj.save()


    def get_queryset(self, request):
        qs = super(NodeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)


class LampAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super(LampAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(node__owner=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "node":
            kwargs["queryset"] = Node.objects.filter(owner=request.user)
        return super(LampAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ZoneAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []
        if not request.user.is_superuser:
            # Exclude owner fields for non superuser
            self.exclude.append('owner')

        return super(ZoneAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if not change:
                obj.owner = request.user
        obj.save()


    def get_queryset(self, request):
        qs = super(ZoneAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "lamps":
                kwargs["queryset"] = Lamp.objects.filter(node__owner=request.user)
            if db_field.name == "sensors":
                kwargs["queryset"] = Sensor.objects.filter(node__owner=request.user)
        return super(ZoneAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

class SensorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super(SensorAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(node__owner=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "node":
                kwargs["queryset"] = Node.objects.filter(owner=request.user)
            if db_field.name == "type":
                kwargs["queryset"] = SensorType.objects.filter(owner=request.user)
        return super(SensorAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class SensorTypeAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []
        if not request.user.is_superuser:
            # Exclude owner fields for non superuser
            self.exclude.append('owner')

        return super(SensorTypeAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if not change:
                obj.owner = request.user
        obj.save()


    def get_queryset(self, request):
        qs = super(SensorTypeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)


class SensorHistoryAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super(SensorHistoryAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(sensor__node__owner=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "node":
                kwargs["queryset"] = Node.objects.filter(owner=request.user)
            if db_field.name == "sensor":
                kwargs["queryset"] = Sensor.objects.filter(node__owner=request.user)
            if db_field.name == "type":
                kwargs["queryset"] = SensorType.objects.filter(owner=request.user)
        return super(SensorHistoryAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)



admin.site.register(Node, NodeAdmin)
admin.site.register(Lamp, LampAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(Sensor, SensorAdmin)
admin.site.register(SensorType, SensorTypeAdmin)
admin.site.register(SensorHistory, SensorHistoryAdmin)
