from django.conf.urls import url
from django.contrib.auth.views import logout, login

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^zones/(?P<zone_id>[0-9]+).html$', views.zone, name='zone'),
    url(r'^nodes/(?P<node_id>[0-9]+).html$', views.node, name='node'),
    url(r'^switch/(?P<lamp_id>[0-9]+)/(?P<status>on|off)$', views.switch, name='switch'),
    url(r'^switch_zones/(?P<zone_id>[0-9]+)/(?P<status>on|off)$', views.switch_zone_by_lamps, name='switch_zone'),
    url(r'^switch_all/(?P<status>on|off)$', views.switch_all_by_lamps, name='switch_all'),
    url(r'^login/$', login),
    url(r'^logout/$', logout),
]