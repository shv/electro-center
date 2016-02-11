from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^status$', views.switch, name='status'),
    url(r'^switch$', views.switch, name='switch'),
    url(r'^switch_one$', views.switch_one, name='switch'),
]