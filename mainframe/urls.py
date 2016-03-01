from django.conf.urls import url
from django.contrib.auth.views import logout, login

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^zones/(?P<zone_id>[0-9]+).html$', views.zone, name='zone'),
    url(r'^nodes/(?P<node_id>[0-9]+).html$', views.node, name='node'),
    url(r'^switch/(?P<lamp_id>[0-9]+)/(?P<status>on|off)$', views.switch, name='switch'),
    url(r'^dim/(?P<lamp_id>[0-9]+)/(?P<value>[0-9]*)$', views.dim, name='dim'),
    url(r'^switch_zones/(?P<zone_id>[0-9]+)/(?P<status>on|off)$', views.switch_zone_by_lamps, name='switch_zone'),
    url(r'^switch_all/(?P<status>on|off)$', views.switch_all_by_lamps, name='switch_all'),
    url(r'^get_sensor_data_for_morris/(?P<sensor_id>[0-9]+)$', views.get_sensor_data_for_morris, name='get_sensor_data_for_morris'),
    url(r'^inventory_status$', views.inventory_status, name='inventory_status'),
    url(r'^login/$', login),
    url(r'^logout/$', logout),
    url(r'^check$', views.check, name='check'),
]