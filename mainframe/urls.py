from django.conf.urls import url
from django.contrib.auth.views import logout, login

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^zones/(?P<zone_id>[0-9]+).html$', views.zone, name='zone'),
    url(r'^nodes/(?P<node_id>[0-9]+).html$', views.node, name='node'),
    url(r'^get_sensor_data_for_morris/(?P<sensor_id>[0-9]+)$', views.get_sensor_data_for_morris, name='get_sensor_data_for_morris'),
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout, name='logout'),
]